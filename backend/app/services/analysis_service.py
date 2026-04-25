import json
import logging
import time
import uuid

from sqlalchemy.orm import Session

from app.llm import get_llm_provider
from app.errors import ExternalProviderError, NoReviewsError
from app.logging_config import timed_operation
from app.models.analysis import Analysis
from app.models.business import Business
from app.models.review import Review
from app.observability import analyses_run, llm_errors, llm_latency, llm_parse_failures
from app.tracing import get_current_trace_id, trace_context, trace_span

logger = logging.getLogger(__name__)

MAX_REVIEWS_FOR_ANALYSIS = 200

_TYPE_FOCUS: dict[str, str] = {
    "restaurant": "service speed, staff friendliness, food quality, wait times, cleanliness, atmosphere, value for money, menu variety, consistency",
    "bar": "drink quality, atmosphere, music/noise, staff friendliness, wait times, pricing, cleanliness, crowd feel",
    "cafe": "coffee/drink quality, food quality, atmosphere, Wi-Fi/workspace suitability, service speed, cleanliness, value",
    "gym": "cleanliness, equipment quality and availability, crowding, staff helpfulness, trainer quality, value, locker rooms",
    "salon": "scheduling ease, wait times, staff professionalism, result quality, cleanliness, pricing, communication",
    "hotel": "cleanliness, front desk service, check-in/out process, amenities, room comfort, noise, value",
    "clinic": "wait times, staff professionalism, doctor communication, cleanliness, scheduling ease, billing clarity",
    "retail": "staff helpfulness, product availability, checkout speed, store organization, cleanliness, return policy, value",
}

_BASE_PROMPT = """\
You are an expert operations and customer-experience consultant.
Analyze the following customer reviews for a {business_type} business.

{focus_instruction}

Return a JSON object with exactly these keys:

- "summary": A concise 2-3 sentence overall assessment written as a consultant would.
- "top_complaints": Up to 5 objects with "label" (short phrase) and "count" (estimated mentions).
- "top_praise": Up to 5 objects with "label" (short phrase) and "count" (estimated mentions).
- "action_items": Up to 5 short actionable improvement suggestions based on the reviews.
- "risk_areas": Up to 3 short descriptions of recurring problems that could hurt the business if unaddressed.
- "recommended_focus": A single sentence stating the #1 area management should prioritize.

Return ONLY valid JSON, no markdown fences or extra text."""


def _build_system_prompt(business_type: str) -> str:
    focus_areas = _TYPE_FOCUS.get(business_type, "")
    if focus_areas:
        focus_instruction = (
            f"Pay special attention to these areas relevant to a {business_type}: {focus_areas}."
        )
    else:
        focus_instruction = "Evaluate all standard customer experience dimensions."
    return _BASE_PROMPT.format(
        business_type=business_type,
        focus_instruction=focus_instruction,
    )


def analyze_reviews(db: Session, business_id: uuid.UUID, trace_id: str | None = None) -> Analysis:
    """Run analysis on stored reviews and persist the result.

    Overwrites any existing analysis for this business.
    """
    business = db.query(Business).filter(Business.id == business_id).first()
    reviews = db.query(Review).filter(Review.business_id == business_id).all()
    if not reviews:
        raise NoReviewsError()

    if len(reviews) > MAX_REVIEWS_FOR_ANALYSIS:
        logger.warning(
            "op=analyze business_id=%s review_count=%d truncated_to=%d",
            business_id,
            len(reviews),
            MAX_REVIEWS_FOR_ANALYSIS,
        )
        reviews = reviews[:MAX_REVIEWS_FOR_ANALYSIS]

    business_type = business.business_type if business else "other"
    system_prompt = _build_system_prompt(business_type)
    review_texts = _format_reviews_for_prompt(reviews)

    tid = trace_id or get_current_trace_id()
    with (
        timed_operation(logger, "llm_call", business_id=business_id, review_count=len(reviews)),
        trace_span(
            trace_context,
            tid,
            "llm_call",
            metadata={"business_id": str(business_id), "review_count": len(reviews)},
        ),
    ):
        result = _call_openai(system_prompt, review_texts)
    result = _normalize_result(result)

    existing = db.query(Analysis).filter(Analysis.business_id == business_id).first()
    if existing:
        # Archive previous version to MongoDB before overwriting (fire-and-forget)
        from app.mongo import archive_analysis

        archive_analysis(
            business_id=str(business_id),
            summary=existing.summary,
            top_complaints=existing.top_complaints,
            top_praise=existing.top_praise,
            action_items=existing.action_items or [],
            risk_areas=existing.risk_areas or [],
            recommended_focus=existing.recommended_focus or "",
            created_at=existing.created_at,
        )

        existing.summary = result["summary"]
        existing.top_complaints = result["top_complaints"]
        existing.top_praise = result["top_praise"]
        existing.action_items = result["action_items"]
        existing.risk_areas = result["risk_areas"]
        existing.recommended_focus = result["recommended_focus"]
        db.commit()
        db.refresh(existing)
        return existing

    analysis = Analysis(
        id=uuid.uuid4(),
        business_id=business_id,
        summary=result["summary"],
        top_complaints=result["top_complaints"],
        top_praise=result["top_praise"],
        action_items=result["action_items"],
        risk_areas=result["risk_areas"],
        recommended_focus=result["recommended_focus"],
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis


def _normalize_result(result: dict) -> dict:
    """Ensure the analysis result always has the expected shape."""
    return {
        "summary": result.get("summary") or "",
        "top_complaints": _normalize_insights(result.get("top_complaints", [])),
        "top_praise": _normalize_insights(result.get("top_praise", [])),
        "action_items": _normalize_strings(result.get("action_items", [])),
        "risk_areas": _normalize_strings(result.get("risk_areas", [])),
        "recommended_focus": str(result.get("recommended_focus") or ""),
    }


def _normalize_insights(items: list) -> list[dict]:
    normalized = []
    for item in items:
        if isinstance(item, dict):
            normalized.append(
                {
                    "label": str(item.get("label", "")),
                    "count": int(item.get("count", 0)),
                }
            )
        elif isinstance(item, str):
            normalized.append({"label": item, "count": 0})
    return normalized


def _normalize_strings(items: list) -> list[str]:
    return [str(item) for item in items if item]


def _format_reviews_for_prompt(reviews: list[Review]) -> str:
    lines = []
    for r in reviews:
        text = r.text or "(no text)"
        lines.append(f"- [{r.rating}/5] {text}")
    return "\n".join(lines)


def _call_openai(system_prompt: str, review_texts: str) -> dict:
    provider = get_llm_provider()
    if not provider:
        return _mock_analysis()

    t0 = time.perf_counter()
    try:
        content = provider.complete([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": review_texts},
        ])
    except Exception as exc:
        llm_errors.add(1)
        logger.error("op=llm_call success=false error=%s detail=%s", type(exc).__name__, exc)
        raise ExternalProviderError("AI analysis failed. Please try again later.") from exc
    finally:
        llm_latency.record((time.perf_counter() - t0) * 1000)

    try:
        result = json.loads(content)
        analyses_run.add(1)
        return result
    except json.JSONDecodeError:
        llm_parse_failures.add(1)
        logger.warning("op=llm_parse success=false content_length=%d", len(content))
        return {"summary": content, "top_complaints": [], "top_praise": []}


def _mock_analysis() -> dict:
    """Return plausible analysis when no OpenAI key is configured."""
    return {
        "summary": (
            "Customers generally appreciate the quality of service and friendly staff, "
            "but frequently mention long wait times and inconsistent food quality. "
            "Overall sentiment is moderately positive."
        ),
        "top_complaints": [
            {"label": "Long wait times", "count": 5},
            {"label": "Inconsistent food quality", "count": 4},
            {"label": "Small portion sizes", "count": 3},
            {"label": "Parking difficulties", "count": 2},
            {"label": "Noise level", "count": 2},
        ],
        "top_praise": [
            {"label": "Friendly and attentive staff", "count": 6},
            {"label": "Great atmosphere and ambiance", "count": 5},
            {"label": "Excellent coffee and drinks", "count": 4},
            {"label": "Clean and well-maintained space", "count": 3},
            {"label": "Good value for money", "count": 3},
        ],
        "action_items": [
            "Hire additional staff during peak hours to reduce wait times",
            "Implement quality checklists for food preparation consistency",
            "Review portion sizing relative to menu pricing",
            "Add signage for nearby parking options",
            "Consider acoustic panels to reduce noise during busy periods",
        ],
        "risk_areas": [
            "Recurring wait time complaints may drive away first-time visitors",
            "Inconsistent food quality erodes trust with regular customers",
            "Parking frustration discourages repeat visits",
        ],
        "recommended_focus": "Prioritize reducing wait times during peak hours, as this is the most frequently cited pain point.",
    }
