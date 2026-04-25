"""Agent tool definitions (OpenAI function-calling format) and execution functions."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models.review import Review
from app.models.workspace_widget import WorkspaceWidget

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
            "name": "pin_widget",
            "description": "Pin an insight or data result to the workspace so the user can keep it visible.",
            "parameters": {
                "type": "object",
                "properties": {
                    "widget_type": {
                        "type": "string",
                        "enum": [
                            "metric_card",
                            "insight_list",
                            "review_list",
                            "summary_card",
                            "comparison_card",
                            "trend_indicator",
                        ],
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
TOOL_WIDGET_TYPES: dict[str, str] = {
    "get_dashboard": "summary_card",
    "query_reviews": "review_list",
    "run_analysis": "insight_list",
    "compare_competitors": "comparison_card",
    "get_review_trends": "trend_indicator",
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
    from app.services.comparison_service import generate_comparison
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


def _pin_widget(
    db: Session,
    business_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    widget_type: str,
    title: str,
    data: dict,
) -> dict:
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
