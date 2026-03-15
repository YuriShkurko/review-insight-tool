import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.errors import BusinessNotFoundError, ComparisonNotReadyError, ExternalProviderError
from app.models.analysis import Analysis
from app.models.business import Business
from app.models.competitor_link import CompetitorLink
from app.models.review import Review
from app.models.user import User
from app.schemas.comparison import (
    CompetitorAdd,
    CompetitorRead,
    ComparisonResponse,
)
from app.services.comparison_service import generate_comparison
from app.services.place_service import get_or_create_business_for_competitor, resolve_place_id_from_url

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/businesses/{business_id}/competitors", tags=["competitors"])

MAX_COMPETITORS = 3


def _build_competitor_read(link: CompetitorLink, comp: Business, db: Session) -> CompetitorRead:
    has_reviews = db.query(Review.id).filter(Review.business_id == comp.id).limit(1).count() > 0
    has_analysis = db.query(Analysis.id).filter(Analysis.business_id == comp.id).limit(1).count() > 0
    return CompetitorRead(
        link_id=link.id,
        business=comp,
        has_reviews=has_reviews,
        has_analysis=has_analysis,
    )


def _get_target_business(
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


@router.post("", response_model=CompetitorRead, status_code=201)
async def add_competitor(
    business_id: uuid.UUID,
    payload: CompetitorAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    target = _get_target_business(business_id, current_user, db)
    place_id = payload.place_id
    google_maps_url = payload.google_maps_url
    if not place_id and google_maps_url:
        place_id, google_maps_url = await resolve_place_id_from_url(google_maps_url)
    if not place_id:
        raise HTTPException(
            status_code=400,
            detail="Could not extract a place identifier. Paste a full or shortened Google Maps URL, or a place ID.",
        )
    existing_count = (
        db.query(CompetitorLink)
        .filter(CompetitorLink.target_business_id == business_id)
        .count()
    )
    if existing_count >= MAX_COMPETITORS:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {MAX_COMPETITORS} competitors allowed. Remove one to add another.",
        )
    competitor = await get_or_create_business_for_competitor(
        db, place_id, current_user.id, google_maps_url, payload.business_type.value
    )
    if competitor.id == target.id:
        raise HTTPException(
            status_code=400,
            detail="Cannot add a business as its own competitor.",
        )
    existing_link = (
        db.query(CompetitorLink)
        .filter(
            CompetitorLink.target_business_id == business_id,
            CompetitorLink.competitor_business_id == competitor.id,
        )
        .first()
    )
    if existing_link:
        return _build_competitor_read(existing_link, competitor, db)
    link = CompetitorLink(
        target_business_id=business_id,
        competitor_business_id=competitor.id,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return _build_competitor_read(link, competitor, db)


@router.get("", response_model=list[CompetitorRead])
def list_competitors(
    business_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_target_business(business_id, current_user, db)
    links = (
        db.query(CompetitorLink)
        .filter(CompetitorLink.target_business_id == business_id)
        .all()
    )
    result = []
    for link in links:
        comp = (
            db.query(Business)
            .filter(Business.id == link.competitor_business_id)
            .first()
        )
        if comp and comp.user_id == current_user.id:
            result.append(_build_competitor_read(link, comp, db))
    return result


@router.delete("/{competitor_business_id}", status_code=204)
def remove_competitor(
    business_id: uuid.UUID,
    competitor_business_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_target_business(business_id, current_user, db)
    link = (
        db.query(CompetitorLink)
        .filter(
            CompetitorLink.target_business_id == business_id,
            CompetitorLink.competitor_business_id == competitor_business_id,
        )
        .first()
    )
    if not link:
        raise HTTPException(status_code=404, detail="Competitor link not found.")
    db.delete(link)
    db.commit()
    return None


@router.post("/comparison", response_model=ComparisonResponse)
def create_comparison(
    business_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return generate_comparison(db, business_id, current_user.id)
    except BusinessNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    except ComparisonNotReadyError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc
    except ExternalProviderError as exc:
        raise HTTPException(status_code=502, detail=exc.message) from exc
