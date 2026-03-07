import json
import uuid

from fastapi import HTTPException
from openai import OpenAI
from sqlalchemy.orm import Session

from app.config import settings
from app.models.analysis import Analysis
from app.models.review import Review

SYSTEM_PROMPT = """\
You are an expert business analyst. Analyze the following customer reviews
and return a JSON object with exactly these keys:

- "summary": A concise 2-3 sentence summary of overall customer sentiment.
- "top_complaints": A list of up to 5 objects, each with "label" (short phrase) and "count" (estimated number of reviews mentioning it).
- "top_praise": A list of up to 5 objects, each with "label" (short phrase) and "count" (estimated number of reviews mentioning it).

Example format:
{
  "summary": "...",
  "top_complaints": [{"label": "Long wait times", "count": 4}],
  "top_praise": [{"label": "Friendly staff", "count": 6}]
}

Return ONLY valid JSON, no markdown fences or extra text."""


def analyze_reviews(db: Session, business_id: uuid.UUID) -> Analysis:
    """Run OpenAI analysis on stored reviews and persist the result.

    Overwrites any existing analysis for this business.
    """
    reviews = db.query(Review).filter(Review.business_id == business_id).all()
    if not reviews:
        raise HTTPException(
            status_code=400,
            detail="No reviews found for this business. Fetch reviews first.",
        )

    review_texts = _format_reviews_for_prompt(reviews)
    result = _call_openai(review_texts)
    result = _normalize_result(result)

    existing = (
        db.query(Analysis).filter(Analysis.business_id == business_id).first()
    )
    if existing:
        existing.summary = result["summary"]
        existing.top_complaints = result["top_complaints"]
        existing.top_praise = result["top_praise"]
        db.commit()
        db.refresh(existing)
        return existing

    analysis = Analysis(
        id=uuid.uuid4(),
        business_id=business_id,
        summary=result["summary"],
        top_complaints=result["top_complaints"],
        top_praise=result["top_praise"],
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis


def _normalize_result(result: dict) -> dict:
    """Ensure the analysis result always has the expected shape."""
    summary = result.get("summary") or ""
    complaints = _normalize_insights(result.get("top_complaints", []))
    praise = _normalize_insights(result.get("top_praise", []))
    return {
        "summary": summary,
        "top_complaints": complaints,
        "top_praise": praise,
    }


def _normalize_insights(items: list) -> list[dict]:
    """Coerce insight items into {label, count} objects.

    Handles both the new format (objects) and the old format (plain strings)
    gracefully so the frontend always gets a consistent shape.
    """
    normalized = []
    for item in items:
        if isinstance(item, dict):
            normalized.append({
                "label": str(item.get("label", "")),
                "count": int(item.get("count", 0)),
            })
        elif isinstance(item, str):
            normalized.append({"label": item, "count": 0})
    return normalized


def _format_reviews_for_prompt(reviews: list[Review]) -> str:
    lines = []
    for r in reviews:
        text = r.text or "(no text)"
        lines.append(f"- [{r.rating}/5] {text}")
    return "\n".join(lines)


def _call_openai(review_texts: str) -> dict:
    if not settings.OPENAI_API_KEY:
        return _mock_analysis()

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": review_texts},
        ],
        temperature=0.3,
    )
    content = response.choices[0].message.content or "{}"
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"summary": content, "top_complaints": [], "top_praise": []}


def _mock_analysis() -> dict:
    """Return a plausible analysis when no OpenAI key is configured."""
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
    }
