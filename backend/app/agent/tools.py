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


def _coerce_pin_widget_arguments(arguments: dict | None) -> dict[str, str | dict]:
    """Strip unknown keys so models that emit extra JSON fields do not break _pin_widget."""
    raw = arguments or {}
    wt = raw.get("widget_type")
    widget_type = wt if isinstance(wt, str) else (str(wt) if wt is not None else "")
    title_raw = raw.get("title")
    title = (
        title_raw
        if isinstance(title_raw, str)
        else (str(title_raw) if title_raw is not None else "Pinned widget")
    )
    data_raw = raw.get("data")
    data = data_raw if isinstance(data_raw, dict) else {}
    return {"widget_type": widget_type, "title": title, "data": data}


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
            "name": "get_rating_distribution",
            "description": (
                "Return review counts grouped by star rating (1-5) for a recent period. "
                "Use for bar charts / histograms (e.g. 'rating breakdown', 'how many 5-star reviews'). "
                "Pin results with widget_type bar_chart."
            ),
            "parameters": {
                "type": "object",
                "properties": {
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
            "name": "get_review_insights",
            "description": (
                "Return consultant-ready synthesized review insights for open-ended questions. "
                "Use focus=negative for worst reviews, complaints, or improvement priorities; "
                "focus=positive for good parts, strengths, praise, or what customers liked; "
                "focus=balanced for general review summaries. Respects period values such as "
                "this_week, this_month, last_month, and past_30d. Returns themes, examples, "
                "limitations, and a recommended action instead of raw review dumps."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "focus": {
                        "type": "string",
                        "enum": ["negative", "positive", "balanced"],
                        "default": "balanced",
                    },
                    "period": {
                        "type": "string",
                        "enum": [
                            "this_week",
                            "this_month",
                            "last_month",
                            "past_7d",
                            "past_30d",
                            "past_90d",
                        ],
                        "default": "past_30d",
                    },
                    "limit": {
                        "type": "integer",
                        "default": 4,
                        "maximum": 6,
                        "description": "Maximum number of themes to return.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_review_change_summary",
            "description": (
                "Compare two review windows for questions like 'what changed compared to last month'. "
                "Returns rating/count deltas, current and previous themes, examples, limitations, "
                "and a recommended action. Use this before answering change-over-time questions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "current_period": {
                        "type": "string",
                        "enum": ["this_week", "this_month", "past_7d", "past_30d"],
                        "default": "this_month",
                    },
                    "previous_period": {
                        "type": "string",
                        "enum": ["last_week", "last_month", "previous_7d", "previous_30d"],
                        "default": "last_month",
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
            "description": (
                "Save a card or chart to the user's dashboard canvas. Call this in the same turn "
                "after a data tool succeeds when the user asked to add, pin, or build the dashboard — "
                "copy that tool's JSON return value into the data field unchanged. "
                "widget_type must match the source: get_dashboard→summary_card; get_top_issues→insight_list; "
                "query_reviews→review_list; run_analysis→insight_list; compare_competitors→comparison_card; "
                "get_review_trends→trend_indicator; get_review_series→line_chart; get_rating_distribution→bar_chart."
            ),
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
    "get_rating_distribution": "bar_chart",
    "get_top_issues": "insight_list",
    "get_review_insights": "summary_card",
    "get_review_change_summary": "summary_card",
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
    if name == "get_rating_distribution":
        try:
            rd_days = int(args.get("days", 30))
        except (TypeError, ValueError):
            rd_days = 30
        return _get_rating_distribution(db, business_id, days=rd_days)
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
    if name == "get_review_insights":
        try:
            parsed_limit = int(args.get("limit", 4))
        except (TypeError, ValueError):
            parsed_limit = 4
        return _get_review_insights(
            db,
            business_id,
            focus=str(args.get("focus", "balanced")),
            period=str(args.get("period", "past_30d")),
            limit=parsed_limit,
        )
    if name == "get_review_change_summary":
        return _get_review_change_summary(
            db,
            business_id,
            current_period=str(args.get("current_period", "this_month")),
            previous_period=str(args.get("previous_period", "last_month")),
        )
    if name == "pin_widget":
        coerced = _coerce_pin_widget_arguments(args)
        return _pin_widget(db, business_id, user_id, **coerced)
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


def _get_rating_distribution(
    db: Session,
    business_id: uuid.UUID,
    *,
    days: int = 30,
) -> dict:
    window_days = max(7, min(90, int(days)))
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

    counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for review in reviews:
        r = int(review.rating) if review.rating is not None else 0
        if r in counts:
            counts[r] += 1

    bars = [{"label": f"{star}★", "value": counts[star]} for star in (1, 2, 3, 4, 5)]
    total = sum(counts.values())

    return {
        "period": f"{window_days}d",
        "days": window_days,
        "bars": bars,
        "total": total,
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


def _period_bounds(period: str, *, now: datetime | None = None) -> tuple[datetime, datetime, str]:
    current = now or datetime.now(UTC)
    today = current.date()
    normalized = period.lower().strip()

    if normalized == "this_week":
        start_date = today - timedelta(days=today.weekday())
        start = datetime.combine(start_date, datetime.min.time(), tzinfo=UTC)
        return start, current, "this week"
    if normalized == "last_week":
        this_week_start = today - timedelta(days=today.weekday())
        start = datetime.combine(this_week_start - timedelta(days=7), datetime.min.time(), UTC)
        end = datetime.combine(this_week_start, datetime.min.time(), UTC)
        return start, end, "last week"
    if normalized == "this_month":
        start = datetime(today.year, today.month, 1, tzinfo=UTC)
        return start, current, "this month"
    if normalized == "last_month":
        first_this_month = datetime(today.year, today.month, 1, tzinfo=UTC)
        last_month_end = first_this_month
        last_month_day = first_this_month.date() - timedelta(days=1)
        start = datetime(last_month_day.year, last_month_day.month, 1, tzinfo=UTC)
        return start, last_month_end, "last month"
    if normalized in {"previous_7d", "previous_30d"}:
        days = 7 if normalized == "previous_7d" else 30
        end = current - timedelta(days=days)
        return end - timedelta(days=days), end, f"previous {days} days"

    days_by_period = {"past_7d": 7, "past_30d": 30, "past_90d": 90}
    days = days_by_period.get(normalized, 30)
    return current - timedelta(days=days), current, f"past {days} days"


def _reviews_in_period(db: Session, business_id: uuid.UUID, period: str) -> tuple[list, str]:
    start, end, label = _period_bounds(period)
    reviews = (
        db.query(Review)
        .filter(
            Review.business_id == business_id,
            Review.published_at >= start,
            Review.published_at < end,
        )
        .order_by(Review.published_at.desc())
        .all()
    )
    return reviews, label


_NEGATIVE_THEMES: dict[str, tuple[str, ...]] = {
    "slow service": ("slow", "wait", "waiting", "delay", "late", "ignored"),
    "staff attitude": ("rude", "attitude", "unfriendly", "dismissive", "impolite"),
    "food or drink quality": ("cold", "stale", "bland", "burnt", "watery", "flat", "bad"),
    "cleanliness": ("dirty", "unclean", "smell", "sticky", "bathroom"),
    "price/value": ("expensive", "overpriced", "price", "value", "cost"),
    "noise or crowding": ("loud", "noise", "crowded", "packed", "music"),
}

_POSITIVE_THEMES: dict[str, tuple[str, ...]] = {
    "friendly service": ("friendly", "kind", "helpful", "attentive", "welcoming"),
    "atmosphere": ("atmosphere", "vibe", "music", "cozy", "ambience", "decor"),
    "food or drink quality": ("tasty", "delicious", "fresh", "great", "excellent", "beer"),
    "speed and convenience": ("quick", "fast", "efficient", "easy"),
    "value": ("fair price", "good price", "value", "worth"),
}


def _match_theme(text: str, themes: dict[str, tuple[str, ...]]) -> str | None:
    lower = text.lower()
    for theme, keywords in themes.items():
        if any(keyword in lower for keyword in keywords):
            return theme
    return None


def _fallback_theme(rating: int, focus: str) -> str:
    if focus == "positive":
        return "positive experience"
    if focus == "negative":
        if rating <= 2:
            return "low-rated experience"
        return "mixed experience with improvement signals"
    if rating >= 4:
        return "positive experience"
    if rating == 3:
        return "mixed experience"
    return "low-rated experience"


def _quote(text: str | None) -> str | None:
    if not text:
        return None
    clean = " ".join(text.split())
    return (clean[:117] + "...") if len(clean) > 120 else clean


def _theme_rows(reviews: list, *, focus: str, limit: int) -> list[dict]:
    if focus == "positive":
        candidates = [r for r in reviews if r.rating >= 3]
        themes = _POSITIVE_THEMES
    elif focus == "negative":
        candidates = [r for r in reviews if r.rating <= 4]
        themes = _NEGATIVE_THEMES
    else:
        candidates = reviews
        themes = {**_NEGATIVE_THEMES, **_POSITIVE_THEMES}

    groups: dict[str, list] = {}
    for review in candidates:
        text = review.text or ""
        theme = _match_theme(text, themes) or _fallback_theme(int(review.rating), focus)
        groups.setdefault(theme, []).append(review)

    def _score(item: tuple[str, list]) -> tuple[float, int]:
        _, grouped = item
        avg = sum(r.rating for r in grouped) / len(grouped)
        if focus == "positive":
            rating_weight = avg / 5
        elif focus == "negative":
            rating_weight = (6 - avg) / 5
        else:
            rating_weight = 1
        return (len(grouped) * rating_weight, len(grouped))

    rows = []
    for theme, grouped in sorted(groups.items(), key=_score, reverse=True)[:limit]:
        avg = round(sum(r.rating for r in grouped) / len(grouped), 2)
        example_review = sorted(
            [r for r in grouped if r.text],
            key=lambda r: (
                abs((3 if focus == "balanced" else (5 if focus == "positive" else 1)) - r.rating),
                len(r.text or ""),
            ),
        )
        rows.append(
            {
                "theme": theme,
                "count": len(grouped),
                "avg_rating": avg,
                "representative_quote": _quote(example_review[0].text) if example_review else None,
            }
        )
    return rows


def _stats(reviews: list) -> dict:
    if not reviews:
        return {"count": 0, "avg_rating": None}
    return {
        "count": len(reviews),
        "avg_rating": round(sum(r.rating for r in reviews) / len(reviews), 2),
    }


def _get_review_insights(
    db: Session,
    business_id: uuid.UUID,
    *,
    focus: str = "balanced",
    period: str = "past_30d",
    limit: int = 4,
) -> dict:
    selected_focus = focus if focus in {"negative", "positive", "balanced"} else "balanced"
    selected_limit = max(1, min(6, int(limit)))
    reviews, label = _reviews_in_period(db, business_id, period)
    stats = _stats(reviews)

    if not reviews:
        return {
            "summary": f"I don't have reviews for {label}, so I can't draw a reliable conclusion.",
            "period": label,
            "focus": selected_focus,
            "review_count": 0,
            "themes": [],
            "examples": [],
            "limitation": f"No dated reviews found for {label}.",
            "recommended_focus": "Fetch or import recent reviews, then rerun the question.",
        }

    themes = _theme_rows(reviews, focus=selected_focus, limit=selected_limit)
    examples = [
        {"theme": row["theme"], "quote": row["representative_quote"]}
        for row in themes
        if row.get("representative_quote")
    ][:2]
    sparse = len(reviews) < 3
    limitation = (
        f"Only {len(reviews)} review(s) found for {label}; treat this as directional."
        if sparse
        else None
    )

    if selected_focus == "positive":
        lead = "The strongest positive signal"
        action = "Reinforce the top praised experience in staff briefings and marketing copy."
        list_key = "top_praise"
    elif selected_focus == "negative":
        lead = "The main improvement signal"
        action = "Start with the highest-count, lowest-rating theme before chasing smaller issues."
        list_key = "top_complaints"
    else:
        lead = "The main review pattern"
        action = (
            "Use the top theme as the next operating focus, then re-check after new reviews land."
        )
        list_key = "issues"

    top_theme = themes[0]["theme"] if themes else "not enough signal"
    summary = (
        f"{lead} for {label} is {top_theme}. "
        f"Based on {stats['count']} review(s), average rating is {stats['avg_rating']}."
    )

    result = {
        "summary": summary,
        "period": label,
        "focus": selected_focus,
        "review_count": stats["count"],
        "avg_rating": stats["avg_rating"],
        "themes": themes,
        "examples": examples,
        "limitation": limitation,
        "recommended_focus": action,
    }
    result[list_key] = [{"label": row["theme"], "count": row["count"]} for row in themes]
    if selected_focus != "positive":
        result["issues"] = [
            {
                "theme": row["theme"],
                "count": row["count"],
                "avg_rating": row["avg_rating"],
                "severity": "critical" if row["avg_rating"] <= 2 else "notable",
                "representative_quote": row["representative_quote"],
            }
            for row in themes
        ]
    return result


def _get_review_change_summary(
    db: Session,
    business_id: uuid.UUID,
    *,
    current_period: str = "this_month",
    previous_period: str = "last_month",
) -> dict:
    current_reviews, current_label = _reviews_in_period(db, business_id, current_period)
    previous_reviews, previous_label = _reviews_in_period(db, business_id, previous_period)
    current = _stats(current_reviews)
    previous = _stats(previous_reviews)

    limitations = []
    if current["count"] < 3:
        limitations.append(f"Only {current['count']} review(s) in {current_label}.")
    if previous["count"] < 3:
        limitations.append(f"Only {previous['count']} review(s) in {previous_label}.")

    rating_delta = None
    if current["avg_rating"] is not None and previous["avg_rating"] is not None:
        rating_delta = round(current["avg_rating"] - previous["avg_rating"], 2)
    count_delta = current["count"] - previous["count"]

    current_themes = _theme_rows(current_reviews, focus="balanced", limit=3)
    previous_themes = _theme_rows(previous_reviews, focus="balanced", limit=3)
    current_top = current_themes[0]["theme"] if current_themes else None
    previous_top = previous_themes[0]["theme"] if previous_themes else None

    if rating_delta is None:
        summary = "There is not enough dated review data in both windows to compare reliably."
    else:
        direction = (
            "improved" if rating_delta > 0 else "declined" if rating_delta < 0 else "held steady"
        )
        summary = (
            f"Compared with {previous_label}, {current_label} {direction}: "
            f"rating changed by {rating_delta:+.2f} and review volume changed by {count_delta:+d}."
        )

    recommended = "Collect more reviews in both periods before making a firm call."
    if rating_delta is not None and abs(rating_delta) >= 0.3:
        recommended = (
            "Investigate the theme shift first; it is large enough to affect customer perception."
        )
    elif current_top and current_top != previous_top:
        recommended = (
            f"Watch the shift from {previous_top} to {current_top}; it may explain the change."
        )

    return {
        "summary": summary,
        "current_period": current_label,
        "previous_period": previous_label,
        "current": current,
        "previous": previous,
        "rating_delta": rating_delta,
        "count_delta": count_delta,
        "current_themes": current_themes,
        "previous_themes": previous_themes,
        "limitation": " ".join(limitations) if limitations else None,
        "recommended_focus": recommended,
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
    return {
        "pinned": True,
        "widget_id": str(widget.id),
        "widget": {
            "id": str(widget.id),
            "widget_type": widget.widget_type,
            "title": widget.title,
            "data": widget.data,
            "position": widget.position,
            "created_at": widget.created_at.isoformat() if widget.created_at else None,
        },
    }
