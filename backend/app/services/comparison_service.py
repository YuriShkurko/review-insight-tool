import json
import logging
import uuid

from sqlalchemy.orm import Session

from app.errors import BusinessNotFoundError, ComparisonNotReadyError, ExternalProviderError
from app.llm import get_llm_provider
from app.logging_config import timed_operation
from app.models.analysis import Analysis
from app.models.business import Business
from app.models.competitor_link import CompetitorLink
from app.observability import comparison_cache_hits, comparison_cache_misses, comparisons_run
from app.schemas.analysis import InsightItem
from app.schemas.comparison import BusinessSnapshot, ComparisonResponse

logger = logging.getLogger(__name__)

_COMPARISON_SYSTEM = """\
You are an expert business and customer-experience consultant.
You will receive structured analysis data for a TARGET business and one or more COMPETITOR businesses (same industry).
Your job is to produce a concise comparison that helps the target business understand:
- Where they are stronger than competitors
- Where they are weaker
- What opportunities they should prioritize

Return a JSON object with exactly these keys:
- "comparison_summary": 2-4 sentences summarizing how the target compares overall to competitors.
- "strengths": List of up to 5 short phrases where the target is doing better than competitors (based on praise, ratings, or fewer complaints).
- "weaknesses": List of up to 5 short phrases where the target lags competitors or has more complaints.
- "opportunities": List of up to 5 short actionable opportunities the target should consider (inspired by competitor strengths or gaps).

Return ONLY valid JSON, no markdown fences or extra text."""


def _snapshot_from_business_and_analysis(
    business: Business, analysis: Analysis | None
) -> BusinessSnapshot | None:
    if not analysis:
        return None
    return BusinessSnapshot(
        business_id=business.id,
        name=business.name,
        business_type=business.business_type,
        avg_rating=business.avg_rating,
        total_reviews=business.total_reviews,
        summary=analysis.summary,
        top_complaints=[InsightItem(**x) for x in analysis.top_complaints],
        top_praise=[InsightItem(**x) for x in analysis.top_praise],
        action_items=analysis.action_items or [],
        risk_areas=analysis.risk_areas or [],
        recommended_focus=analysis.recommended_focus or "",
    )


def _format_snapshots_for_prompt(
    target: BusinessSnapshot, competitors: list[BusinessSnapshot]
) -> str:
    """Serialize target and competitors into a string for the LLM."""

    def snapshot_to_dict(s: BusinessSnapshot) -> dict:
        return {
            "name": s.name,
            "business_type": s.business_type,
            "avg_rating": s.avg_rating,
            "total_reviews": s.total_reviews,
            "summary": s.summary,
            "top_complaints": [{"label": i.label, "count": i.count} for i in s.top_complaints],
            "top_praise": [{"label": i.label, "count": i.count} for i in s.top_praise],
            "action_items": s.action_items,
            "risk_areas": s.risk_areas,
            "recommended_focus": s.recommended_focus,
        }

    data = {
        "target": snapshot_to_dict(target),
        "competitors": [snapshot_to_dict(c) for c in competitors],
    }
    return json.dumps(data, indent=2)


def _call_openai_comparison(prompt_text: str) -> dict:
    provider = get_llm_provider()
    if not provider:
        return _mock_comparison()
    try:
        content = provider.complete([
            {"role": "system", "content": _COMPARISON_SYSTEM},
            {"role": "user", "content": prompt_text},
        ])
    except Exception as exc:
        logger.error(
            "op=comparison_llm success=false error=%s detail=%s",
            type(exc).__name__,
            exc,
        )
        raise ExternalProviderError(
            "Comparison generation failed. Please try again later."
        ) from exc
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        logger.warning("op=comparison_parse success=false content_length=%d", len(content))
        return _mock_comparison()


def _mock_comparison() -> dict:
    return {
        "comparison_summary": "Comparison insights are available when OpenAI is configured.",
        "strengths": [],
        "weaknesses": [],
        "opportunities": [],
    }


def _normalize_comparison_result(raw: dict) -> dict:
    return {
        "comparison_summary": str(raw.get("comparison_summary") or ""),
        "strengths": [str(s) for s in (raw.get("strengths") or []) if s],
        "weaknesses": [str(w) for w in (raw.get("weaknesses") or []) if w],
        "opportunities": [str(o) for o in (raw.get("opportunities") or []) if o],
    }


def generate_comparison(
    db: Session, business_id: uuid.UUID, user_id: uuid.UUID
) -> ComparisonResponse:
    """Build comparison of target business vs linked competitors that have analysis.

    Requires: target has analysis, at least one linked competitor has analysis.
    """
    target_business = (
        db.query(Business).filter(Business.id == business_id, Business.user_id == user_id).first()
    )
    if not target_business:
        raise BusinessNotFoundError()

    target_analysis = db.query(Analysis).filter(Analysis.business_id == business_id).first()
    target_snapshot = _snapshot_from_business_and_analysis(target_business, target_analysis)
    if not target_snapshot:
        raise ComparisonNotReadyError(
            "Run analysis on this business before generating a comparison."
        )

    links = db.query(CompetitorLink).filter(CompetitorLink.target_business_id == business_id).all()
    competitor_snapshots: list[BusinessSnapshot] = []
    for link in links:
        comp_business = (
            db.query(Business).filter(Business.id == link.competitor_business_id).first()
        )
        if not comp_business or comp_business.user_id != user_id:
            continue
        comp_analysis = (
            db.query(Analysis).filter(Analysis.business_id == link.competitor_business_id).first()
        )
        snap = _snapshot_from_business_and_analysis(comp_business, comp_analysis)
        if snap:
            competitor_snapshots.append(snap)

    if not competitor_snapshots:
        raise ComparisonNotReadyError(
            "Add at least one competitor and run analysis on them before generating a comparison."
        )

    # Check MongoDB cache before expensive LLM call
    from app.mongo import cache_comparison, get_cached_comparison

    competitor_id_strs = sorted(str(s.business_id) for s in competitor_snapshots)
    cached = get_cached_comparison(str(business_id), competitor_id_strs)
    if cached:
        comparison_cache_hits.add(1)
        logger.info("op=comparison_cache_hit business_id=%s", business_id)
        return ComparisonResponse(
            target=target_snapshot,
            competitors=competitor_snapshots,
            comparison_summary=cached["comparison_summary"],
            strengths=cached["strengths"],
            weaknesses=cached["weaknesses"],
            opportunities=cached["opportunities"],
        )

    comparison_cache_misses.add(1)
    prompt_text = _format_snapshots_for_prompt(target_snapshot, competitor_snapshots)
    with timed_operation(
        logger,
        "comparison_llm",
        business_id=business_id,
        competitor_count=len(competitor_snapshots),
    ):
        raw = _call_openai_comparison(prompt_text)
    normalized = _normalize_comparison_result(raw)

    # Cache in MongoDB (fire-and-forget)
    cache_comparison(
        business_id=str(business_id),
        competitor_ids=competitor_id_strs,
        target_snapshot=target_snapshot.model_dump(mode="json"),
        competitor_snapshots=[s.model_dump(mode="json") for s in competitor_snapshots],
        comparison_summary=normalized["comparison_summary"],
        strengths=normalized["strengths"],
        weaknesses=normalized["weaknesses"],
        opportunities=normalized["opportunities"],
    )

    comparisons_run.add(1)
    return ComparisonResponse(
        target=target_snapshot,
        competitors=competitor_snapshots,
        comparison_summary=normalized["comparison_summary"],
        strengths=normalized["strengths"],
        weaknesses=normalized["weaknesses"],
        opportunities=normalized["opportunities"],
    )
