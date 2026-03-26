"""Debug tool implementations for the Review Insight Tool MCP server.

All tools are read-only except sandbox_reset_user, which requires explicit
confirm=True and only works when REVIEW_PROVIDER=offline.

Sensitive data rules (enforced throughout):
- Never return JWT_SECRET_KEY, DATABASE_URL, or any API key value
- Never return password hashes
- Never return raw review text (PII risk)
- API key presence is always reported as a boolean only

Tool inventory (14 total):

System / config:
  system_status()              — provider, keys-set flags, DB reachable, Railway
  migration_status()           — Alembic current vs head revisions
  health_probe()               — DB ping + provider + trace buffer (DEBUG_TRACE)

Sandbox / data:
  sandbox_catalog_summary()    — offline manifest: businesses, scenarios, review counts
  recent_businesses(limit)     — N most recent businesses with owner/analysis info
  db_table_counts()            — row counts for users/businesses/reviews/analyses/links

Business / user:
  business_snapshot(id)        — full debug view for one business UUID
  user_summary(email|id)       — business count, review totals, account info

Frontend debug selector:
  debug_selector_status()      — CTRL+click selector config, env flag, + current snapshot
  ui_snapshot()                — latest CTRL+click element snapshot (raw)

Tracing dipstick (require DEBUG_TRACE=true):
  trace_journey(trace_id)      — ordered span tree: route→db→llm→exit
  recent_traces(limit)         — newest-first trace summaries with span counts
  mutation_log(entity_id)      — all write-flagged spans for an entity
  llm_call_log(business_id)    — all LLM call spans for a business

Mutating (guarded):
  sandbox_reset_user(confirm, email|id) — deletes offline_* businesses (confirm=True required)

Example session:
    health_probe()                          # is everything alive?
    recent_traces(limit=5)                  # what just happened?
    trace_journey("abc-123-def")            # deep dive on one request
    llm_call_log("biz-uuid-here")          # why was that analysis slow?
    mutation_log("biz-uuid-here")          # what did we write to the DB?
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

_DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "offline"


def _make_session():
    """Create a DB session from the current settings, raising a clear error if the URL is invalid."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.config import settings

    try:
        _engine = create_engine(settings.DATABASE_URL)
        _session_factory = sessionmaker(bind=_engine, autocommit=False, autoflush=False)
        return _session_factory()
    except Exception as exc:
        raise RuntimeError(
            f"Cannot connect to database — DATABASE_URL may be malformed or missing: "
            f"{str(exc).split(chr(10))[0][:100]}"
        ) from exc


def register_tools(mcp: Any) -> None:
    """Register all debug tools onto a FastMCP instance."""

    # ── 1. system_status ──────────────────────────────────────────────────────

    @mcp.tool(
        name="system_status",
        description=(
            "Returns a safe summary of the current backend configuration: "
            "review provider, which API keys are set (boolean only, never values), "
            "CORS origins, whether the database is reachable, JWT expiry minutes, "
            "and whether the server is running on Railway. "
            "Never exposes secrets or connection strings."
        ),
    )
    def system_status() -> dict:
        from sqlalchemy import create_engine, text

        from app.config import _running_on_railway, settings

        db_ok = False
        db_error = None
        try:
            _engine = create_engine(settings.DATABASE_URL)
            with _engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            db_ok = True
        except Exception as exc:
            db_error = str(exc).split("\n")[0][:120]

        cors_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
        if settings.CORS_ORIGINS:
            cors_origins.extend(o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip())

        return {
            "review_provider": settings.REVIEW_PROVIDER,
            "openai_key_set": bool(settings.OPENAI_API_KEY),
            "outscraper_key_set": bool(settings.OUTSCRAPER_API_KEY),
            "google_places_key_set": bool(settings.GOOGLE_PLACES_API_KEY),
            "jwt_algorithm": settings.JWT_ALGORITHM,
            "jwt_expire_minutes": settings.JWT_EXPIRE_MINUTES,
            "jwt_secret_is_default": settings.JWT_SECRET_KEY == "change-me-in-production",
            "cors_origins": cors_origins,
            "on_railway": _running_on_railway(),
            "db_reachable": db_ok,
            "db_error": db_error,
        }

    # ── 2. migration_status ───────────────────────────────────────────────────

    @mcp.tool(
        name="migration_status",
        description=(
            "Returns Alembic migration state: the current DB revision(s), "
            "the expected head revision(s), and whether the schema is up to date. "
            "Useful for diagnosing startup failures and staging schema drift."
        ),
    )
    def migration_status() -> dict:
        from alembic.config import Config
        from alembic.runtime.migration import MigrationContext
        from alembic.script import ScriptDirectory
        from sqlalchemy import create_engine

        from app.config import settings

        alembic_cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        script = ScriptDirectory.from_config(alembic_cfg)
        expected_heads = [s.revision for s in script.get_revisions("heads")]

        current_heads: list[str] = []
        db_error = None
        try:
            _engine = create_engine(settings.DATABASE_URL)
            with _engine.connect() as conn:
                ctx = MigrationContext.configure(conn)
                current_heads = list(ctx.get_current_heads())
        except Exception as exc:
            db_error = str(exc).split("\n")[0][:120]

        at_head = set(current_heads) == set(expected_heads) if not db_error else None

        return {
            "current_revisions": current_heads,
            "expected_head_revisions": expected_heads,
            "at_head": at_head,
            "db_error": db_error,
        }

    # ── 3. sandbox_catalog_summary ────────────────────────────────────────────

    @mcp.tool(
        name="sandbox_catalog_summary",
        description=(
            "Returns a summary of the offline sandbox catalog: total businesses, "
            "scenarios, per-scenario structure, and review file counts. "
            "Only meaningful when REVIEW_PROVIDER=offline. "
            "Useful for diagnosing import/reset issues without the UI."
        ),
    )
    def sandbox_catalog_summary() -> dict:
        from app.config import settings

        manifest_path = _DATA_DIR / "manifest.json"
        if not manifest_path.exists():
            return {"error": "manifest.json not found", "data_dir": str(_DATA_DIR)}

        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)

        businesses = manifest.get("businesses", [])
        scenarios = manifest.get("scenarios", {})

        def review_count(entry: dict) -> int:
            rel = entry.get("reviews_file")
            if not rel:
                return 0
            fp = _DATA_DIR / rel
            if not fp.exists():
                return 0
            try:
                with open(fp, encoding="utf-8") as f2:
                    data = json.load(f2)
                return len(data) if isinstance(data, list) else 0
            except (json.JSONDecodeError, OSError):
                return 0

        by_place = {b["place_id"]: b for b in businesses}
        biz_summary = [
            {
                "place_id": b["place_id"],
                "name": b["name"],
                "type": b.get("business_type", "other"),
                "review_count": review_count(b),
                "reviews_file": b.get("reviews_file"),
            }
            for b in businesses
        ]

        scenario_summary = {}
        for sid, sc in scenarios.items():
            main_entry = by_place.get(sc["main"], {})
            scenario_summary[sid] = {
                "description": sc.get("description", ""),
                "main": {"place_id": sc["main"], "name": main_entry.get("name", "unknown")},
                "competitors": [
                    {
                        "place_id": cid,
                        "name": by_place.get(cid, {}).get("name", "unknown"),
                    }
                    for cid in sc.get("competitors", [])
                ],
            }

        total_reviews = sum(review_count(b) for b in businesses)

        return {
            "provider_is_offline": settings.REVIEW_PROVIDER == "offline",
            "total_businesses": len(businesses),
            "total_scenarios": len(scenarios),
            "total_reviews_on_disk": total_reviews,
            "businesses": biz_summary,
            "scenarios": scenario_summary,
        }

    # ── 4. business_snapshot ──────────────────────────────────────────────────

    @mcp.tool(
        name="business_snapshot",
        description=(
            "Returns a debug snapshot for a specific business by its UUID. "
            "Includes name, place_id, business type, avg rating, review count, "
            "whether analysis exists, analysis timestamp, competitor names, "
            "and is_competitor flag. Owner-agnostic (debug-only). "
            "Does not return raw review text."
        ),
    )
    def business_snapshot(business_id: str) -> dict:
        from app.models.analysis import Analysis
        from app.models.business import Business
        from app.models.competitor_link import CompetitorLink
        from app.models.user import User

        try:
            biz_uuid = uuid.UUID(business_id)
        except ValueError:
            return {"error": f"Invalid UUID: {business_id!r}"}

        try:
            db = _make_session()
        except RuntimeError as exc:
            return {"error": str(exc)}
        try:
            business = db.query(Business).filter(Business.id == biz_uuid).first()
            if not business:
                return {"error": f"Business {business_id} not found"}

            analysis = db.query(Analysis).filter(Analysis.business_id == biz_uuid).first()

            # Competitors this business has (if it's a primary business)
            competitor_links = (
                db.query(CompetitorLink)
                .filter(CompetitorLink.target_business_id == biz_uuid)
                .all()
            )
            competitor_names: list[str] = []
            for link in competitor_links:
                comp = (
                    db.query(Business).filter(Business.id == link.competitor_business_id).first()
                )
                if comp:
                    competitor_names.append(f"{comp.name} ({comp.place_id})")

            # Owner email (not password)
            owner = db.query(User).filter(User.id == business.user_id).first()

            return {
                "id": str(business.id),
                "name": business.name,
                "place_id": business.place_id,
                "business_type": business.business_type,
                "avg_rating": business.avg_rating,
                "total_reviews": business.total_reviews,
                "is_competitor": business.is_competitor,
                "address": business.address,
                "has_analysis": analysis is not None,
                "analysis_created_at": analysis.created_at.isoformat() if analysis else None,
                "competitor_count": len(competitor_links),
                "competitors": competitor_names,
                "owner_email": owner.email if owner else None,
                "created_at": business.created_at.isoformat() if business.created_at else None,
                "updated_at": business.updated_at.isoformat() if business.updated_at else None,
            }
        finally:
            db.close()

    # ── 5. user_summary ───────────────────────────────────────────────────────

    @mcp.tool(
        name="user_summary",
        description=(
            "Returns a debug summary for a user by email or user UUID. "
            "Includes email, business count, total reviews across all their businesses, "
            "and account creation time. Never returns password hash or tokens."
        ),
    )
    def user_summary(email: str | None = None, user_id: str | None = None) -> dict:
        from app.models.business import Business
        from app.models.review import Review
        from app.models.user import User

        if not email and not user_id:
            return {"error": "Provide either email or user_id"}

        try:
            db = _make_session()
        except RuntimeError as exc:
            return {"error": str(exc)}
        try:
            user = None
            if email:
                user = db.query(User).filter(User.email == email).first()
            elif user_id:
                try:
                    uid = uuid.UUID(user_id)
                except ValueError:
                    return {"error": f"Invalid UUID: {user_id!r}"}
                user = db.query(User).filter(User.id == uid).first()

            if not user:
                return {"error": "User not found"}

            businesses = db.query(Business).filter(Business.user_id == user.id).all()
            biz_ids = [b.id for b in businesses]
            total_reviews = 0
            if biz_ids:
                total_reviews = db.query(Review).filter(Review.business_id.in_(biz_ids)).count()

            return {
                "id": str(user.id),
                "email": user.email,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "business_count": len(businesses),
                "total_reviews_stored": total_reviews,
                "businesses": [
                    {
                        "id": str(b.id),
                        "name": b.name,
                        "place_id": b.place_id,
                        "is_competitor": b.is_competitor,
                        "total_reviews": b.total_reviews,
                    }
                    for b in businesses
                ],
            }
        finally:
            db.close()

    # ── 6. recent_businesses ──────────────────────────────────────────────────

    @mcp.tool(
        name="recent_businesses",
        description=(
            "Returns the N most recently created businesses (default 10, max 50). "
            "Shows id, name, place_id, owner email, review count, and whether analysis exists. "
            "Useful for triaging what was just imported or created."
        ),
    )
    def recent_businesses(limit: int = 10) -> dict:
        from app.models.analysis import Analysis
        from app.models.business import Business
        from app.models.user import User

        limit = min(max(1, limit), 50)
        try:
            db = _make_session()
        except RuntimeError as exc:
            return {"error": str(exc)}
        try:
            rows = db.query(Business).order_by(Business.created_at.desc()).limit(limit).all()
            results = []
            for b in rows:
                owner = db.query(User).filter(User.id == b.user_id).first()
                has_analysis = (
                    db.query(Analysis).filter(Analysis.business_id == b.id).first() is not None
                )
                results.append(
                    {
                        "id": str(b.id),
                        "name": b.name,
                        "place_id": b.place_id,
                        "business_type": b.business_type,
                        "is_competitor": b.is_competitor,
                        "total_reviews": b.total_reviews,
                        "has_analysis": has_analysis,
                        "owner_email": owner.email if owner else None,
                        "created_at": b.created_at.isoformat() if b.created_at else None,
                    }
                )
            return {"count": len(results), "businesses": results}
        finally:
            db.close()

    # ── 7. db_table_counts ────────────────────────────────────────────────────

    @mcp.tool(
        name="db_table_counts",
        description=(
            "Returns row counts for all main tables: users, businesses, reviews, "
            "analyses, competitor_links. Quick health snapshot of the database."
        ),
    )
    def db_table_counts() -> dict:
        from app.models.analysis import Analysis
        from app.models.business import Business
        from app.models.competitor_link import CompetitorLink
        from app.models.review import Review
        from app.models.user import User

        try:
            db = _make_session()
        except RuntimeError as exc:
            return {"error": str(exc)}
        try:
            return {
                "users": db.query(User).count(),
                "businesses": db.query(Business).count(),
                "reviews": db.query(Review).count(),
                "analyses": db.query(Analysis).count(),
                "competitor_links": db.query(CompetitorLink).count(),
            }
        except Exception as exc:
            return {"error": str(exc).split("\n")[0][:120]}
        finally:
            db.close()

    # ── Dipstick tools (require DEBUG_TRACE for meaningful data) ──────────────

    from debug.dipstick import (
        get_debug_selector_status,
        get_health_probe,
        get_llm_call_log,
        get_mutation_log,
        get_recent_traces,
        get_trace_journey,
        get_ui_snapshot,
    )

    @mcp.tool(
        name="trace_journey",
        description=(
            "Returns the ordered span tree for a single request trace from the live backend. "
            "Requires DEBUG_TRACE=true. Pass the trace_id from an X-Trace-Id response header "
            "or from recent_traces. Shows every span: route_enter, db_query, llm_call, route_exit."
        ),
    )
    def trace_journey(trace_id: str) -> dict:
        return get_trace_journey(trace_id)

    @mcp.tool(
        name="health_probe",
        description=(
            "Checks the liveness of all backend components: database (live SELECT 1), "
            "review provider (from config), and trace buffer (enabled/disabled + size). "
            "Quick engine-oil check — call this first when something feels off."
        ),
    )
    def health_probe() -> dict:
        return get_health_probe()

    @mcp.tool(
        name="recent_traces",
        description=(
            "Returns the N most recent request traces from the live backend, newest first. "
            "Each entry shows trace_id, endpoint, started_at, and span_count. "
            "Requires DEBUG_TRACE=true on the running backend."
        ),
    )
    def recent_traces(limit: int = 20) -> dict:
        return get_recent_traces(limit=limit)

    @mcp.tool(
        name="mutation_log",
        description=(
            "Returns all mutation spans recorded for a given entity_id (e.g. a business UUID). "
            "A span is a mutation when its metadata contains mutation=true. "
            "Shows every write operation with trace_id, operation name, and timestamp. "
            "Requires DEBUG_TRACE=true on the running backend."
        ),
    )
    def mutation_log(entity_id: str) -> dict:
        return get_mutation_log(entity_id=entity_id)

    @mcp.tool(
        name="llm_call_log",
        description=(
            "Returns all LLM call spans for a given business_id from the live backend. "
            "Shows model call duration, success, and which trace each call belongs to. "
            "Useful for diagnosing slow analysis or runaway token usage. "
            "Requires DEBUG_TRACE=true on the running backend."
        ),
    )
    def llm_call_log(business_id: str) -> dict:
        return get_llm_call_log(business_id=business_id)

    @mcp.tool(
        name="ui_snapshot",
        description=(
            "Fetches the latest frontend UI element snapshot captured by the debug selector. "
            "To populate it: hold CTRL and click any element in the browser (requires "
            "NEXT_PUBLIC_DEBUG_TRAIL=true). Returns the selected element tree: tag, CSS path, "
            "React component name, bounding rect, text content, data-* attributes, and "
            "immediate children. Multi-select is supported — each CTRL+click adds an element. "
            "Double-tap CTRL in the browser to clear the selection. "
            "Requires DEBUG_TRACE=true on the backend."
        ),
    )
    def ui_snapshot() -> dict:
        return get_ui_snapshot()

    @mcp.tool(
        name="debug_selector_status",
        description=(
            "Returns the full state of the frontend CTRL+click debug selector. "
            "Checks whether NEXT_PUBLIC_DEBUG_TRAIL=true is set in frontend/.env.local, "
            "then fetches the latest UI snapshot from the running backend. "
            "Also documents the complete selector workflow: "
            "hold CTRL → cursor becomes crosshair; CTRL+click → purple glow on the element "
            "([data-debug-sel='primary']) and dashed outlines on all children; "
            "double-tap CTRL to clear; ◉ Debug panel → Selector tab to inspect selection. "
            "Use this first to verify the selector is enabled before calling ui_snapshot."
        ),
    )
    def debug_selector_status() -> dict:
        return get_debug_selector_status()

    # ── 8. sandbox_reset_user (guarded mutating) ──────────────────────────────

    @mcp.tool(
        name="sandbox_reset_user",
        description=(
            "Deletes all offline_* businesses for a given user (by email or user_id). "
            "MUTATING — requires confirm=True. "
            "Only works when REVIEW_PROVIDER=offline. "
            "Returns the count of deleted businesses. "
            "Does not affect non-sandbox (non offline_*) data."
        ),
    )
    def sandbox_reset_user(
        confirm: bool,
        email: str | None = None,
        user_id: str | None = None,
    ) -> dict:
        from app.config import settings
        from app.models.business import Business
        from app.models.user import User

        if not confirm:
            return {"error": "confirm must be True to proceed. This is a destructive operation."}

        if settings.REVIEW_PROVIDER != "offline":
            return {
                "error": (
                    f"sandbox_reset_user is only allowed when REVIEW_PROVIDER=offline. "
                    f"Current provider: {settings.REVIEW_PROVIDER!r}"
                )
            }

        if not email and not user_id:
            return {"error": "Provide either email or user_id"}

        try:
            db = _make_session()
        except RuntimeError as exc:
            return {"error": str(exc)}

        try:
            user = None
            if email:
                user = db.query(User).filter(User.email == email).first()
            elif user_id:
                try:
                    uid = uuid.UUID(user_id)
                except ValueError:
                    return {"error": f"Invalid UUID: {user_id!r}"}
                user = db.query(User).filter(User.id == uid).first()

            if not user:
                return {"error": "User not found"}

            to_delete = (
                db.query(Business)
                .filter(
                    Business.user_id == user.id,
                    Business.place_id.startswith("offline_"),
                )
                .all()
            )
            count = len(to_delete)
            for b in to_delete:
                db.delete(b)
            db.commit()

            return {
                "deleted": count,
                "user_email": user.email,
                "message": f"Deleted {count} offline business(es) for {user.email}.",
            }
        finally:
            db.close()
