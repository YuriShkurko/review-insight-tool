"""Agent tool definitions (OpenAI function-calling format) and execution functions."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal, get_args

from sqlalchemy.orm import Session

from app.models.review import Review
from app.models.workspace_widget import WorkspaceWidget

# ---------------------------------------------------------------------------
# Widget type registry — single source of truth for both the tool schema and
# the REST schema validation (schemas/agent.py imports WidgetType from here).
# ---------------------------------------------------------------------------

WidgetType = Literal[
    "metric_card",
    "insight_list",
    "review_list",
    "summary_card",
    "comparison_card",
    "trend_indicator",
    "line_chart",
    "bar_chart",
]

WIDGET_TYPES: frozenset[str] = frozenset(get_args(WidgetType))

# ---------------------------------------------------------------------------
# OpenAI tool definitions
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "get_dashboard",
            "description": "Get the business overview: average rating, review count, AI analysis summary, top complaints and praise.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_reviews",
            "description": "Retrieve customer reviews with optional filters.",
            "parameters": {
                "type": "object",
                "properties": {
                    "min_rating": {"type": "integer", "minimum": 1, "maximum": 5},
                    "max_rating": {"type": "integer", "minimum": 1, "maximum": 5},
                    "keyword": {"type": "string", "description": "Filter by word in review text"},
                    "date_from": {"type": "string", "description": "ISO date string (YYYY-MM-DD)"},
                    "date_to": {"type": "string", "description": "ISO date string (YYYY-MM-DD)"},
                    "limit": {"type": "integer", "default": 20, "maximum": 100},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_analysis",
            "description": "Run AI analysis on all current reviews and return the full result.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_competitors",
            "description": "Generate an AI comparison of this business vs its linked competitors.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_review_trends",
            "description": "Compare review volume and rating between the current period and the prior period.",
            "parameters": {
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "enum": ["7d", "14d", "30d"],
                        "default": "7d",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_review_series",
            "description": "Return chart-ready review time series grouped by day for a recent period.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "enum": [3, 7, 14, 30],
                        "default": 7,
                        "description": "Number of days to include (rolling window ending today).",
                    },
                    "metric": {
                        "type": "string",
                        "enum": ["count", "avg_rating", "both"],
                        "default": "both",
                        "description": "Which metric to include in the response.",
                    },
                    "group_by": {
                        "type": "string",
                        "enum": ["day"],
                        "default": "day",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_issues",
            "description": (
                "Return the top ranked issues from recent reviews with severity labels "
                "(critical/notable/minor) and representative quotes. Use this instead of "
                "query_reviews when answering open-ended quality or improvement questions "
                "(e.g. 'what's wrong', 'what should we fix', 'what are customers complaining about')."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "default": 5,
                        "maximum": 10,
                        "description": "Number of top issues to return.",
                    },
                    "days": {
                        "type": "integer",
                        "default": 30,
                        "description": "Recency window in days (7-90).",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "pin_widget",
            "description": "Pin an insight or data result to the workspace so the user can keep it visible.",
            "parameters": {
                "type": "object",
                "properties": {
                    "widget_type": {
                        "type": "string",
                        "enum": sorted(WIDGET_TYPES),
                    },
                    "title": {"type": "string"},
                    "data": {"type": "object"},
                },
                "required": ["widget_type", "title", "data"],
            },
        },
    },
]

# Maps tool name → widget_type hint for tool_result SSE events
TOOL_WIDGET_TYPES: dict[str, str | None] = {
    "get_dashboard": "summary_card",
    "query_reviews": "review_list",
    "run_analysis": "insight_list",
    "compare_competitors": "comparison_card",
    "get_review_trends": "trend_indicator",
    "get_review_series": "line_chart",
    "get_top_issues": "insight_list",
    "pin_widget": None,
}

# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


def execute_tool(
    name: str,
    args: dict,
    db: Session,
    business_id: uuid.UUID,
    user_id: uuid.UUID,
) -> dict:
    if name == "get_dashboard":
        return _get_dashboard(db, business_id, user_id)
    if name == "query_reviews":
        return _query_reviews(db, business_id, **args)
    if name == "run_analysis":
        return _run_analysis(db, business_id)
    if name == "compare_competitors":
        return _compare_competitors(db, business_id, user_id)
    if name == "get_review_trends":
        return _get_review_trends(db, business_id, args.get("period", "7d"))
    if name == "get_review_series":
        raw_days = args.get("days", 7)
        raw_metric = args.get("metric", "both")
        try:
            parsed_days = int(raw_days)
        except (TypeError, ValueError):
            parsed_days = 7
        return _get_review_series(
            db,
            business_id,
            days=parsed_days,
            metric=str(raw_metric),
        )
    if name == "get_top_issues":
        try:
            parsed_limit = int(args.get("limit", 5))
        except (TypeError, ValueError):
            parsed_limit = 5
        try:
            parsed_days = int(args.get("days", 30))
        except (TypeError, ValueError):
            parsed_days = 30
        return _get_top_issues(db, business_id, limit=parsed_limit, days=parsed_days)
    if name == "pin_widget":
        return _pin_widget(db, business_id, user_id, **args)
    return {"error": f"Unknown tool: {name}"}


def _get_dashboard(db: Session, business_id: uuid.UUID, user_id: uuid.UUID) -> dict:
    from app.services.dashboard_service import get_dashboard

    result = get_dashboard(db, business_id, user_id)
    return result.model_dump(mode="json")


def _query_reviews(
    db: Session,
    business_id: uuid.UUID,
    *,
    min_rating: int | None = None,
    max_rating: int | None = None,
    keyword: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 20,
) -> dict:
    q = db.query(Review).filter(Review.business_id == business_id)
    if min_rating is not None:
        q = q.filter(Review.rating >= min_rating)
    if max_rating is not None:
        q = q.filter(Review.rating <= max_rating)
    if keyword:
        q = q.filter(Review.text.ilike(f"%{keyword}%"))
    if date_from:
        q = q.filter(Review.published_at >= datetime.fromisoformat(date_from))
    if date_to:
        q = q.filter(Review.published_at <= datetime.fromisoformat(date_to))
    reviews = q.order_by(Review.published_at.desc()).limit(min(limit, 100)).all()
    return {
        "count": len(reviews),
        "reviews": [
            {
                "id": str(r.id),
                "rating": r.rating,
                "text": r.text,
                "author": r.author,
                "published_at": r.published_at.isoformat() if r.published_at else None,
            }
            for r in reviews
        ],
    }


def _run_analysis(db: Session, business_id: uuid.UUID) -> dict:
    from app.services.analysis_service import analyze_reviews

    analysis = analyze_reviews(db, business_id)
    return {
        "summary": analysis.summary,
        "top_complaints": analysis.top_complaints,
        "top_praise": analysis.top_praise,
        "action_items": analysis.action_items,
        "risk_areas": analysis.risk_areas,
        "recommended_focus": analysis.recommended_focus,
    }


def _compare_competitors(db: Session, business_id: uuid.UUID, user_id: uuid.UUID) -> dict:
    from app.models.analysis import Analysis
    from app.models.competitor_link import CompetitorLink
    from app.services.analysis_service import analyze_reviews
    from app.services.comparison_service import generate_comparison
    from app.services.review_service import fetch_reviews_for_business

    links = db.query(CompetitorLink).filter(CompetitorLink.target_business_id == business_id).all()
    for link in links:
        comp = link.competitor_business
        if comp is None or comp.user_id != user_id:
            continue
        has_analysis = db.query(Analysis).filter(Analysis.business_id == comp.id).first()
        if not has_analysis:
            if not comp.total_reviews:
                fetch_reviews_for_business(db, comp)
            analyze_reviews(db, comp.id)

    result = generate_comparison(db, business_id, user_id)
    return result.model_dump(mode="json")


def _get_review_trends(db: Session, business_id: uuid.UUID, period: str) -> dict:
    days = {"7d": 7, "14d": 14, "30d": 30}.get(period, 7)
    now = datetime.now(UTC)
    current_start = now - timedelta(days=days)
    previous_start = current_start - timedelta(days=days)

    def _stats(reviews: list) -> dict:
        if not reviews:
            return {"count": 0, "avg_rating": None}
        return {
            "count": len(reviews),
            "avg_rating": round(sum(r.rating for r in reviews) / len(reviews), 2),
        }

    current = (
        db.query(Review)
        .filter(Review.business_id == business_id, Review.published_at >= current_start)
        .all()
    )
    previous = (
        db.query(Review)
        .filter(
            Review.business_id == business_id,
            Review.published_at >= previous_start,
            Review.published_at < current_start,
        )
        .all()
    )

    curr = _stats(current)
    prev = _stats(previous)
    change_pct = None
    if prev["count"] > 0:
        change_pct = round((curr["count"] - prev["count"]) / prev["count"] * 100, 1)

    return {"period": period, "current": curr, "previous": prev, "change_pct": change_pct}


def _get_review_series(
    db: Session,
    business_id: uuid.UUID,
    *,
    days: int = 7,
    metric: str = "both",
) -> dict:
    allowed_days = {3, 7, 14, 30}
    window_days = days if days in allowed_days else 7
    selected_metric = metric if metric in {"count", "avg_rating", "both"} else "both"

    today = datetime.now(UTC).date()
    start_date = today - timedelta(days=window_days - 1)

    reviews = (
        db.query(Review)
        .filter(
            Review.business_id == business_id,
            Review.published_at >= datetime.combine(start_date, datetime.min.time(), tzinfo=UTC),
        )
        .order_by(Review.published_at.asc())
        .all()
    )

    buckets: dict[str, dict[str, float | int | None]] = {}
    cursor = start_date
    while cursor <= today:
        key = cursor.isoformat()
        buckets[key] = {"date": key, "count": 0, "avg_rating": None, "_rating_sum": 0.0}
        cursor += timedelta(days=1)

    for review in reviews:
        if not review.published_at:
            continue
        day_key = review.published_at.date().isoformat()
        if day_key not in buckets:
            continue
        bucket = buckets[day_key]
        count = int(bucket["count"])
        bucket["count"] = count + 1
        bucket["_rating_sum"] = float(bucket["_rating_sum"] or 0.0) + float(review.rating)

    series: list[dict[str, int | float | str | None]] = []
    for day in sorted(buckets.keys()):
        bucket = buckets[day]
        count = int(bucket["count"])
        avg_rating = None
        if count > 0:
            avg_rating = round(float(bucket["_rating_sum"]) / count, 2)
        series.append({"date": day, "count": count, "avg_rating": avg_rating})

    total_reviews = sum(int(point["count"] or 0) for point in series)
    rated_points = [
        float(point["avg_rating"]) for point in series if point["avg_rating"] is not None
    ]
    period_avg_rating = round(sum(rated_points) / len(rated_points), 2) if rated_points else None

    return {
        "period": f"{window_days}d",
        "days": window_days,
        "group_by": "day",
        "metric": selected_metric,
        "from": start_date.isoformat(),
        "to": today.isoformat(),
        "series": series,
        "summary": {
            "total_reviews": total_reviews,
            "avg_rating": period_avg_rating,
        },
    }


def _get_top_issues(
    db: Session,
    business_id: uuid.UUID,
    *,
    limit: int = 5,
    days: int = 30,
) -> dict:
    from app.models.analysis import Analysis

    window_days = max(7, min(90, int(days)))
    limit = max(1, min(10, int(limit)))

    now = datetime.now(UTC)
    window_start = now - timedelta(days=window_days)

    reviews = (
        db.query(Review)
        .filter(
            Review.business_id == business_id,
            Review.published_at >= window_start,
        )
        .all()
    )

    if not reviews:
        return {"issues": [], "period": f"{window_days}d", "total_reviews_analyzed": 0}

    analysis = db.query(Analysis).filter(Analysis.business_id == business_id).first()
    complaint_themes = [c["label"] for c in (analysis.top_complaints or [])] if analysis else []

    def _is_recent(review) -> bool:
        return bool(review.published_at and (now - review.published_at).days <= 14)

    def _matches_theme(text: str, theme: str) -> bool:
        tl = text.lower()
        thl = theme.lower()
        if thl in tl:
            return True
        return any(w in tl for w in thl.split() if len(w) > 4)

    # Group reviews by complaint theme if analysis data is available, else by star bucket
    groups: dict[str, list] = {}

    if complaint_themes:
        for theme in complaint_themes:
            matched = [r for r in reviews if r.text and _matches_theme(r.text, theme)]
            if matched:
                groups[theme] = matched
        matched_ids = {id(r) for g in groups.values() for r in g}
        leftover = [r for r in reviews if id(r) not in matched_ids]
        if leftover:
            groups["Other feedback"] = leftover
    else:
        for r in reviews:
            if r.rating <= 2:
                bucket = "Critical issues (1-2 stars)"
            elif r.rating == 3:
                bucket = "Mixed feedback (3 stars)"
            else:
                bucket = "Positive feedback (4-5 stars)"
            groups.setdefault(bucket, []).append(r)

    def _severity(avg_r: float, has_recent: bool) -> str:
        if avg_r <= 1.5 and has_recent:
            return "critical"
        if avg_r <= 2.5:
            return "notable"
        return "minor"

    def _pick_quote(group_reviews: list) -> str | None:
        candidates = [r for r in group_reviews if r.text and r.rating <= 3]
        if not candidates:
            candidates = [r for r in group_reviews if r.text]
        if not candidates:
            return None
        text = min(candidates, key=lambda r: len(r.text or "")).text or ""
        return (text[:117] + "…") if len(text) > 120 else text

    issues = []
    for theme, group_reviews in groups.items():
        avg_r = sum(r.rating for r in group_reviews) / len(group_reviews)
        has_recent = any(_is_recent(r) for r in group_reviews)
        # Score: count x recency multiplier x rating-severity weight
        recency_mult = 1.5 if has_recent else 1.0
        rating_penalty = max(0.1, (5 - avg_r) / 4)
        score = len(group_reviews) * recency_mult * rating_penalty

        issues.append(
            {
                "theme": theme,
                "count": len(group_reviews),
                "avg_rating": round(avg_r, 2),
                "severity": _severity(avg_r, has_recent),
                "representative_quote": _pick_quote(group_reviews),
                "_score": score,
            }
        )

    issues.sort(key=lambda x: x["_score"], reverse=True)
    for issue in issues:
        del issue["_score"]

    return {
        "issues": issues[:limit],
        "period": f"{window_days}d",
        "total_reviews_analyzed": len(reviews),
    }


def _pin_widget(
    db: Session,
    business_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    widget_type: str,
    title: str,
    data: dict,
) -> dict:
    if widget_type not in WIDGET_TYPES:
        return {"error": f"Unknown widget_type '{widget_type}'", "pinned": False}

    # Place new widget after existing ones
    existing_count = (
        db.query(WorkspaceWidget)
        .filter(
            WorkspaceWidget.business_id == business_id,
            WorkspaceWidget.user_id == user_id,
        )
        .count()
    )
    widget = WorkspaceWidget(
        id=uuid.uuid4(),
        business_id=business_id,
        user_id=user_id,
        widget_type=widget_type,
        title=title,
        data=data,
        position=existing_count,
    )
    db.add(widget)
    db.commit()
    db.refresh(widget)
    return {"widget_id": str(widget.id), "pinned": True}
