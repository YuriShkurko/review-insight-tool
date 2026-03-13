import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.logging_config import timed_operation
from app.models.business import Business
from app.models.user import User
from app.schemas.business import BusinessCreate, BusinessRead
from app.services.place_service import get_or_create_business, parse_place_id_from_url

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/businesses", tags=["businesses"])


@router.post("", response_model=BusinessRead, status_code=201)
async def create_business(
    payload: BusinessCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    place_id = payload.place_id
    google_maps_url = payload.google_maps_url

    if not place_id and google_maps_url:
        place_id = parse_place_id_from_url(google_maps_url)

    if not place_id:
        raise HTTPException(
            status_code=400,
            detail="Provide a valid place_id or a Google Maps URL containing one.",
        )

    with timed_operation(logger, "create_business", user_id=current_user.id, type=payload.business_type.value):
        business = await get_or_create_business(
            db, place_id, current_user.id, google_maps_url, payload.business_type.value
        )
    return business


@router.get("", response_model=list[BusinessRead])
def list_businesses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Business)
        .filter(Business.user_id == current_user.id)
        .order_by(Business.created_at.desc())
        .all()
    )


@router.get("/{business_id}", response_model=BusinessRead)
def get_business(
    business_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    business = (
        db.query(Business)
        .filter(Business.id == business_id, Business.user_id == current_user.id)
        .first()
    )
    if not business:
        raise HTTPException(status_code=404, detail="Business not found.")
    return business
