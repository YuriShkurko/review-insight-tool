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
    "pie_chart",
    "donut_chart",
    "horizontal_bar_chart",
    "comparison_chart",
]

WIDGET_TYPES: frozenset[str] = frozenset(get_args(WidgetType))

# Names of all data-fetching tools that can be referenced by source_tool in pin_widget.
DATA_TOOL_NAMES: list[str] = [
    "get_dashboard",
    "query_reviews",
    "run_analysis",
    "compare_competitors",
    "get_review_trends",
    "get_review_series",
    "get_rating_distribution",
    "get_top_issues",
    "get_review_insights",
    "get_review_change_summary",
    "create_custom_chart_data",
]

# Inference keywords that require an explicit uncertainty_note in
# create_custom_chart_data results. Detected case-insensitively against
# source_summary, labels, and notes.
_INFERENCE_KEYWORDS: tuple[str, ...] = (
    "infer",
    "inferred",
    "assume",
    "assumed",
    "guess",
    "name-based",
    "name based",
    "name-inferred",
    "gender",
    "ethnic",
    "demographic",
    "predicted",
    "estimated",
)


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
            "name": "create_custom_chart_data",
            "description": (
                "Build a chart-ready payload from data you derived yourself (composing other tools, "
                "custom buckets, or inferred segments). The result IS the widget data — pin it next "
                "with source_tool='create_custom_chart_data'. Use this when no fixed data tool covers "
                "the user's question (e.g. complaints by inferred name attribute, custom themes, "
                "composed metrics). When inference is involved (e.g. inferring gender from names), "
                "uncertainty_note is REQUIRED and must say so plainly. The executor validates the "
                "shape; invalid shapes are rejected with a clear error."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "widget_type": {
                        "type": "string",
                        "enum": [
                            "bar_chart",
                            "horizontal_bar_chart",
                            "pie_chart",
                            "donut_chart",
                            "insight_list",
                        ],
                        "description": "Widget shape this payload is for.",
                    },
                    "labels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Segment labels for chart variants. Required for bar/pie/donut.",
                    },
                    "values": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": (
                            "Numeric values aligned with labels. Required for bar/pie/donut. "
                            "All values must be finite and >= 0."
                        ),
                    },
                    "items": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": (
                            "List items for widget_type=insight_list. Each item should have a "
                            "'theme' or 'label' key plus optional 'count'/'severity'/'representative_quote'."
                        ),
                    },
                    "title_hint": {
                        "type": "string",
                        "description": "Short label describing the segmentation (e.g. 'Complaints by inferred name attribute').",
                    },
                    "notes": {
                        "type": "string",
                        "description": "Short caveat or observation rendered alongside the chart.",
                    },
                    "source_summary": {
                        "type": "string",
                        "description": (
                            "One-sentence summary of which existing tool(s) this was derived from "
                            "and how. Used to surface methodology to the user."
                        ),
                    },
                    "uncertainty_note": {
                        "type": "string",
                        "description": (
                            "Required when inference is involved (gender from names, demographic "
                            "guesses, predicted attributes). State the limitation plainly, e.g. "
                            "'Names were used to infer likely gender; this may be inaccurate.'"
                        ),
                    },
                },
                "required": ["widget_type", "source_summary"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "pin_widget",
            "description": (
                "Save a supported card or chart to the user's dashboard canvas. "
                "Always set source_tool to the name of the data tool you just called — "
                "the executor uses it to wire the exact tool result to the widget. "
                "widget_type MUST be in the compatibility table for that source_tool "
                "(see the system prompt's COMPATIBILITY TABLE). If the user asks for a "
                "chart shape your source_tool cannot produce, EITHER pick a different "
                "source_tool that does, OR call create_custom_chart_data first and pin "
                "with source_tool='create_custom_chart_data'. Do not invent new "
                "widget_types and do not force an incompatible pair — the executor "
                "rejects mismatches and the turn is lost."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "widget_type": {
                        "type": "string",
                        "enum": sorted(WIDGET_TYPES),
                    },
                    "title": {"type": "string"},
                    "source_tool": {
                        "type": "string",
                        "enum": DATA_TOOL_NAMES,
                        "description": (
                            "Name of the data tool whose result to pin. "
                            "Must match the tool called immediately before this pin_widget call."
                        ),
                    },
                    "data": {
                        "type": "object",
                        "description": "Tool result payload. Omit or leave empty — the executor fills it from source_tool.",
                    },
                },
                "required": ["widget_type", "title", "source_tool"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_workspace",
            "description": (
                "List the current dashboard widgets with exact widget IDs, titles, types, "
                "and positions. Use this before remove, duplicate, or set_dashboard_order "
                "when you need to identify existing dashboard widgets."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remove_widget",
            "description": (
                "Remove a dashboard widget by exact widget_id UUID. Never guess or fabricate "
                "widget IDs; ask the user to clarify if the target widget is ambiguous."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "widget_id": {
                        "type": "string",
                        "format": "uuid",
                        "description": "Exact UUID of the workspace widget to remove.",
                    }
                },
                "required": ["widget_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "clear_dashboard",
            "description": (
                "Remove every widget from the current dashboard in one atomic action. "
                "Use this when the user asks to clear, wipe, reset, replace, rebuild, "
                "or start over with the dashboard. Prefer this over calling "
                "remove_widget repeatedly."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "duplicate_widget",
            "description": (
                "Copy an existing dashboard widget by exact widget_id UUID. The copy is created "
                "directly from the persisted row, so its data is always renderable — never goes "
                "through pin_widget or source_tool resolution. Use this when the user asks for "
                "another copy of a widget on the dashboard. Never guess widget IDs."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "widget_id": {
                        "type": "string",
                        "format": "uuid",
                        "description": "Exact UUID of the workspace widget to duplicate.",
                    }
                },
                "required": ["widget_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_dashboard_order",
            "description": (
                "Set the exact dashboard widget order using the current persisted widget IDs. "
                "Use this for reverse, reorder, arrange, move, or after duplicating/removing "
                "widgets when the user requested a final order. Include every widget that "
                "should appear in the final order. Never guess widget IDs; ask for "
                "clarification if the requested order is ambiguous."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "widget_ids": {
                        "type": "array",
                        "items": {"type": "string", "format": "uuid"},
                        "description": "Exact widget IDs in the desired dashboard order.",
                    }
                },
                "required": ["widget_ids"],
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
    "get_rating_distribution": "donut_chart",
    "get_top_issues": "horizontal_bar_chart",
    "get_review_insights": "summary_card",
    "get_review_change_summary": "comparison_chart",
    "create_custom_chart_data": None,
    "pin_widget": None,
    "get_workspace": None,
    "remove_widget": None,
    "clear_dashboard": None,
    "duplicate_widget": None,
    "set_dashboard_order": None,
}

# Per-tool acceptable widget types. The model occasionally picks a chart
# that is incompatible with the data shape (e.g. pie_chart of a time series),
# which renders "No chart data available." on the dashboard. The executor
# uses this map to refuse the pin before persisting an unrenderable widget.
TOOL_COMPATIBLE_WIDGETS: dict[str, frozenset[str]] = {
    "get_dashboard": frozenset({"summary_card", "metric_card"}),
    "query_reviews": frozenset({"review_list"}),
    "run_analysis": frozenset({"insight_list", "summary_card"}),
    "compare_competitors": frozenset({"comparison_card", "comparison_chart"}),
    "get_review_trends": frozenset({"trend_indicator", "metric_card"}),
    "get_review_series": frozenset({"line_chart"}),
    "get_rating_distribution": frozenset({"bar_chart", "donut_chart", "pie_chart"}),
    "get_top_issues": frozenset({"horizontal_bar_chart", "bar_chart", "insight_list"}),
    "get_review_insights": frozenset({"summary_card", "insight_list"}),
    "get_review_change_summary": frozenset({"comparison_chart", "comparison_card"}),
    # create_custom_chart_data builds chart-ready payloads itself; widget_type
    # is enforced inside the tool, but pin_widget still gates against this map.
    "create_custom_chart_data": frozenset(
        {"bar_chart", "horizontal_bar_chart", "pie_chart", "donut_chart", "insight_list"}
    ),
}


def format_compatibility_for_prompt() -> str:
    """Render the source_tool → allowed widget_types map for the system prompt.

    Sourced from TOOL_COMPATIBLE_WIDGETS so the prompt and the executor's
    safety rail can never drift.
    """
    lines = []
    for source_tool in sorted(TOOL_COMPATIBLE_WIDGETS):
        allowed = sorted(TOOL_COMPATIBLE_WIDGETS[source_tool])
        lines.append(f"  - {source_tool} -> {', '.join(allowed)}")
    return "\n".join(lines)


# Inline the compatibility hint into each data-tool description at module
# load. The model sees the rule at tool-pick time, not just in the system
# prompt — this is what closes the "agent picks an incompatible widget"
# loop after the v3.6.1 hotfix added the executor-side rejection.
def _enrich_tool_descriptions() -> None:
    for tool_def in TOOL_DEFINITIONS:
        fn = tool_def.get("function") or {}
        name = fn.get("name")
        if name in TOOL_COMPATIBLE_WIDGETS:
            allowed = ", ".join(sorted(TOOL_COMPATIBLE_WIDGETS[name]))
            existing = fn.get("description") or ""
            if "Compatible widget_types" not in existing:
                fn["description"] = (
                    f"{existing} Compatible widget_types when pinning this result: [{allowed}]."
                ).strip()


_enrich_tool_descriptions()

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
    if name == "create_custom_chart_data":
        return _create_custom_chart_data(args)
    if name == "pin_widget":
        coerced = _coerce_pin_widget_arguments(args)
        return _pin_widget(db, business_id, user_id, **coerced)
    if name == "get_workspace":
        return _get_workspace(db, business_id, user_id)
    if name == "remove_widget":
        return _remove_widget(db, business_id, user_id, widget_id=str(args.get("widget_id", "")))
    if name == "clear_dashboard":
        return _clear_dashboard(db, business_id, user_id)
    if name == "duplicate_widget":
        return _duplicate_widget(
            db, business_id, user_id, widget_id=str(args.get("widget_id", ""))
        )
    if name == "set_dashboard_order":
        raw_widget_ids = args.get("widget_ids")
        widget_ids = raw_widget_ids if isinstance(raw_widget_ids, list) else []
        return _set_dashboard_order(db, business_id, user_id, widget_ids=widget_ids)
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
    slices = [
        {
            "label": f"{star} star",
            "value": counts[star],
            "percent": round((counts[star] / total) * 100, 1) if total else 0,
        }
        for star in (1, 2, 3, 4, 5)
    ]

    return {
        "period": f"{window_days}d",
        "days": window_days,
        "bars": bars,
        "slices": slices,
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

    top_issues = issues[:limit]
    return {
        "issues": top_issues,
        "bars": [{"label": issue["theme"], "value": issue["count"]} for issue in top_issues],
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
    review_rows = [
        {
            "id": str(review.id),
            "rating": review.rating,
            "text": review.text,
            "author": review.author,
            "published_at": review.published_at.isoformat() if review.published_at else None,
        }
        for review in sorted(
            reviews,
            key=lambda r: (
                -r.rating if selected_focus == "positive" else r.rating,
                -(r.published_at or datetime.min.replace(tzinfo=UTC)).timestamp(),
            ),
        )[:6]
    ]
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
        "bars": [{"label": row["theme"], "value": row["count"]} for row in themes],
        "examples": examples,
        "reviews": review_rows,
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


def _remove_widget(
    db: Session,
    business_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    widget_id: str,
) -> dict:
    try:
        parsed_widget_id = uuid.UUID(str(widget_id))
    except (TypeError, ValueError):
        return {"removed": False, "error": "Invalid widget_id UUID."}

    widget = (
        db.query(WorkspaceWidget)
        .filter(
            WorkspaceWidget.id == parsed_widget_id,
            WorkspaceWidget.business_id == business_id,
            WorkspaceWidget.user_id == user_id,
        )
        .first()
    )
    if not widget:
        return {"removed": False, "widget_id": str(parsed_widget_id), "error": "Widget not found."}

    db.delete(widget)
    db.commit()
    return {"removed": True, "widget_id": str(parsed_widget_id)}


def _clear_dashboard(db: Session, business_id: uuid.UUID, user_id: uuid.UUID) -> dict:
    widgets = (
        db.query(WorkspaceWidget)
        .filter(
            WorkspaceWidget.business_id == business_id,
            WorkspaceWidget.user_id == user_id,
        )
        .all()
    )
    removed_ids = [str(widget.id) for widget in widgets]
    for widget in widgets:
        db.delete(widget)
    db.commit()
    return {"cleared": True, "removed_count": len(removed_ids), "widget_ids": removed_ids}


def _get_workspace(db: Session, business_id: uuid.UUID, user_id: uuid.UUID) -> dict:
    widgets = (
        db.query(WorkspaceWidget)
        .filter(
            WorkspaceWidget.business_id == business_id,
            WorkspaceWidget.user_id == user_id,
        )
        .order_by(WorkspaceWidget.position)
        .all()
    )
    return {
        "widgets": [
            {
                "id": str(widget.id),
                "title": widget.title,
                "widget_type": widget.widget_type,
                "position": widget.position,
            }
            for widget in widgets
        ],
        "widget_ids": [str(widget.id) for widget in widgets],
    }


def _duplicate_widget(
    db: Session,
    business_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    widget_id: str,
) -> dict:
    """Copy an existing WorkspaceWidget row directly.

    Bypasses pin_widget / source_tool resolution: the new row is a deep copy
    of an existing persisted widget, so its data is renderable by construction.
    Returns the same shape as `_pin_widget` so the executor's SSE emission
    path can treat duplication as another `widget_added` event.
    """
    import copy

    try:
        parsed_widget_id = uuid.UUID(str(widget_id))
    except (TypeError, ValueError):
        return {"duplicated": False, "error": "Invalid widget_id UUID."}

    source = (
        db.query(WorkspaceWidget)
        .filter(
            WorkspaceWidget.id == parsed_widget_id,
            WorkspaceWidget.business_id == business_id,
            WorkspaceWidget.user_id == user_id,
        )
        .first()
    )
    if not source:
        return {
            "duplicated": False,
            "widget_id": str(parsed_widget_id),
            "error": "Widget not found.",
        }

    existing_count = (
        db.query(WorkspaceWidget)
        .filter(
            WorkspaceWidget.business_id == business_id,
            WorkspaceWidget.user_id == user_id,
        )
        .count()
    )

    base_title = source.title or "Pinned widget"
    new_title = base_title if base_title.endswith(" (copy)") else f"{base_title} (copy)"

    new_widget = WorkspaceWidget(
        id=uuid.uuid4(),
        business_id=business_id,
        user_id=user_id,
        widget_type=source.widget_type,
        title=new_title,
        data=copy.deepcopy(source.data) if source.data is not None else {},
        position=existing_count,
    )
    db.add(new_widget)
    db.commit()
    db.refresh(new_widget)
    return {
        "duplicated": True,
        "widget_id": str(new_widget.id),
        "source_widget_id": str(parsed_widget_id),
        "widget": {
            "id": str(new_widget.id),
            "widget_type": new_widget.widget_type,
            "title": new_widget.title,
            "data": new_widget.data,
            "position": new_widget.position,
            "created_at": new_widget.created_at.isoformat() if new_widget.created_at else None,
        },
    }


def _set_dashboard_order(
    db: Session,
    business_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    widget_ids: list,
) -> dict:
    parsed_ids: list[uuid.UUID] = []
    for raw_id in widget_ids:
        try:
            parsed_ids.append(uuid.UUID(str(raw_id)))
        except (TypeError, ValueError):
            return {"reordered": False, "error": f"Invalid widget_id UUID: {raw_id!r}."}

    if len(parsed_ids) != len(set(parsed_ids)):
        return {"reordered": False, "error": "widget_ids must not contain duplicates."}

    rows = (
        db.query(WorkspaceWidget)
        .filter(
            WorkspaceWidget.business_id == business_id,
            WorkspaceWidget.user_id == user_id,
        )
        .order_by(WorkspaceWidget.position)
        .all()
    )
    existing_ids = [row.id for row in rows]
    existing_set = set(existing_ids)
    requested_set = set(parsed_ids)

    missing = [str(widget_id) for widget_id in parsed_ids if widget_id not in existing_set]
    omitted = [str(widget_id) for widget_id in existing_ids if widget_id not in requested_set]
    if missing or omitted:
        return {
            "reordered": False,
            "error": (
                "widget_ids must include exactly the current dashboard widgets. "
                "Call get_workspace or ask the user to clarify if you do not know the full order."
            ),
            "missing_widget_ids": missing,
            "omitted_widget_ids": omitted,
            "current_widget_ids": [str(widget_id) for widget_id in existing_ids],
        }

    for position, widget_id in enumerate(parsed_ids):
        db.query(WorkspaceWidget).filter(
            WorkspaceWidget.id == widget_id,
            WorkspaceWidget.business_id == business_id,
            WorkspaceWidget.user_id == user_id,
        ).update({"position": position})
    db.commit()

    ordered_widgets = (
        db.query(WorkspaceWidget)
        .filter(
            WorkspaceWidget.business_id == business_id,
            WorkspaceWidget.user_id == user_id,
        )
        .order_by(WorkspaceWidget.position)
        .all()
    )
    return {
        "reordered": True,
        "widget_ids": [str(widget.id) for widget in ordered_widgets],
        "widgets": [
            {
                "id": str(widget.id),
                "widget_type": widget.widget_type,
                "title": widget.title,
                "data": widget.data,
                "position": widget.position,
                "created_at": widget.created_at.isoformat() if widget.created_at else None,
            }
            for widget in ordered_widgets
        ],
    }


def _create_custom_chart_data(args: dict) -> dict:
    """Validate and package an agent-derived chart payload.

    The model uses this when no fixed data tool covers the question (e.g.
    inferred segments, custom buckets, composed metrics). The result IS the
    widget data — pin it next with source_tool='create_custom_chart_data'.
    Validation is strict: invalid shapes are rejected so an empty/misleading
    chart can never reach the dashboard.
    """
    import math

    raw = args or {}
    widget_type = raw.get("widget_type")
    if not isinstance(widget_type, str) or widget_type not in {
        "bar_chart",
        "horizontal_bar_chart",
        "pie_chart",
        "donut_chart",
        "insight_list",
    }:
        return {
            "error": (
                "widget_type must be one of bar_chart, horizontal_bar_chart, "
                "pie_chart, donut_chart, insight_list."
            ),
        }

    source_summary = raw.get("source_summary")
    if not isinstance(source_summary, str) or not source_summary.strip():
        return {"error": "source_summary is required and must be a non-empty string."}

    notes = raw.get("notes") if isinstance(raw.get("notes"), str) else None
    title_hint = raw.get("title_hint") if isinstance(raw.get("title_hint"), str) else None
    uncertainty_note = (
        raw.get("uncertainty_note") if isinstance(raw.get("uncertainty_note"), str) else None
    )

    # Inference detection: if the source/labels/title smell like inferred
    # attributes, an explicit uncertainty_note is mandatory. The product
    # rule is: never claim a heuristic is fact.
    inference_haystack_parts: list[str] = [source_summary, notes or "", title_hint or ""]
    labels_raw = raw.get("labels")
    if isinstance(labels_raw, list):
        inference_haystack_parts.extend(str(label) for label in labels_raw)
    haystack = " ".join(inference_haystack_parts).lower()
    looks_inferred = any(keyword in haystack for keyword in _INFERENCE_KEYWORDS)
    if looks_inferred and (not uncertainty_note or not uncertainty_note.strip()):
        return {
            "error": (
                "uncertainty_note is required when the segmentation is inferred "
                "(e.g. gender from names, demographic guesses). State the limitation "
                "plainly so the chart cannot be read as fact."
            ),
        }

    if widget_type == "insight_list":
        items_raw = raw.get("items")
        if not isinstance(items_raw, list) or not items_raw:
            return {"error": "items must be a non-empty list for widget_type=insight_list."}
        items: list[dict] = []
        for entry in items_raw:
            if not isinstance(entry, dict):
                return {"error": "Each item must be an object with at least 'theme' or 'label'."}
            theme = entry.get("theme") or entry.get("label")
            if not isinstance(theme, str) or not theme.strip():
                return {"error": "Each item must have a non-empty 'theme' or 'label'."}
            items.append({**entry, "theme": theme})
        result = {
            "widget_type": widget_type,
            "items": items,
            "source_summary": source_summary,
        }
        if notes:
            result["notes"] = notes
        if title_hint:
            result["title_hint"] = title_hint
        if uncertainty_note:
            result["uncertainty_note"] = uncertainty_note
        return result

    # Chart variants (bar / horizontal_bar / pie / donut) — labels + values.
    if not isinstance(labels_raw, list) or not labels_raw:
        return {
            "error": f"labels is required and must be a non-empty list for widget_type={widget_type}."
        }
    values_raw = raw.get("values")
    if not isinstance(values_raw, list) or not values_raw:
        return {
            "error": f"values is required and must be a non-empty list for widget_type={widget_type}."
        }
    if len(labels_raw) != len(values_raw):
        return {
            "error": (
                f"labels and values must be the same length "
                f"(got {len(labels_raw)} labels, {len(values_raw)} values)."
            ),
        }

    cleaned_labels: list[str] = []
    cleaned_values: list[float] = []
    for label, value in zip(labels_raw, values_raw, strict=True):
        if not isinstance(label, str) or not label.strip():
            return {"error": "All labels must be non-empty strings."}
        try:
            num = float(value)
        except (TypeError, ValueError):
            return {"error": f"Value for label '{label}' must be numeric."}
        if not math.isfinite(num):
            return {"error": f"Value for label '{label}' must be finite."}
        if num < 0:
            return {"error": f"Value for label '{label}' must be >= 0."}
        cleaned_labels.append(label.strip())
        cleaned_values.append(num)

    if widget_type in {"pie_chart", "donut_chart"}:
        positive_count = sum(1 for v in cleaned_values if v > 0)
        if positive_count < 2:
            return {
                "error": (
                    "pie_chart/donut_chart need at least 2 slices with value > 0; "
                    "use a different widget type for sparse data."
                ),
            }

    bars = [
        {"label": label, "value": value}
        for label, value in zip(cleaned_labels, cleaned_values, strict=True)
    ]
    total = sum(cleaned_values)
    slices = [
        {
            "label": label,
            "value": value,
            "percent": round((value / total) * 100, 1) if total > 0 else 0,
        }
        for label, value in zip(cleaned_labels, cleaned_values, strict=True)
    ]

    result = {
        "widget_type": widget_type,
        "labels": cleaned_labels,
        "values": cleaned_values,
        "bars": bars,
        "slices": slices,
        "total": total,
        "source_summary": source_summary,
    }
    if notes:
        result["notes"] = notes
    if title_hint:
        result["title_hint"] = title_hint
    if uncertainty_note:
        result["uncertainty_note"] = uncertainty_note
    return result
