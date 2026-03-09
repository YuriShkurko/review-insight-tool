import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.analysis import Analysis
from app.models.business import Business
from app.schemas.dashboard import DashboardResponse


def get_dashboard(
    db: Session, business_id: uuid.UUID, user_id: uuid.UUID
) -> DashboardResponse:
    """Aggregate business data, review stats, and analysis into a single response.

    Never crashes on missing data -- returns clean defaults for every field.
    """
    business = (
        db.query(Business)
        .filter(Business.id == business_id, Business.user_id == user_id)
        .first()
    )
    if not business:
        raise HTTPException(status_code=404, detail="Business not found.")

    analysis = (
        db.query(Analysis).filter(Analysis.business_id == business_id).first()
    )

    return DashboardResponse(
        business_name=business.name,
        business_type=business.business_type,
        address=business.address,
        avg_rating=business.avg_rating,
        total_reviews=business.total_reviews,
        top_complaints=analysis.top_complaints if analysis else [],
        top_praise=analysis.top_praise if analysis else [],
        ai_summary=analysis.summary if analysis else None,
        action_items=analysis.action_items if analysis else [],
        risk_areas=analysis.risk_areas if analysis else [],
        recommended_focus=analysis.recommended_focus if analysis else None,
    )
