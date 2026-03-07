import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.business import Business
from app.models.review import Review
from app.models.user import User
from app.schemas.analysis import AnalysisRead
from app.schemas.review import ReviewRead
from app.services.analysis_service import analyze_reviews
from app.services.review_service import fetch_reviews_for_business

router = APIRouter(prefix="/businesses/{business_id}", tags=["reviews"])


def _get_business_for_user(
    business_id: uuid.UUID, user: User, db: Session
) -> Business:
    business = (
        db.query(Business)
        .filter(Business.id == business_id, Business.user_id == user.id)
        .first()
    )
    if not business:
        raise HTTPException(status_code=404, detail="Business not found.")
    return business


@router.post("/fetch-reviews", response_model=list[ReviewRead])
def trigger_fetch_reviews(
    business_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    business = _get_business_for_user(business_id, current_user, db)
    reviews = fetch_reviews_for_business(db, business)
    return reviews


@router.get("/reviews", response_model=list[ReviewRead])
def list_reviews(
    business_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_business_for_user(business_id, current_user, db)
    return (
        db.query(Review)
        .filter(Review.business_id == business_id)
        .order_by(Review.published_at.desc())
        .all()
    )


@router.post("/analyze", response_model=AnalysisRead)
def trigger_analysis(
    business_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_business_for_user(business_id, current_user, db)
    return analyze_reviews(db, business_id)
