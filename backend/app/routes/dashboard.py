import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.errors import BusinessNotFoundError
from app.logging_config import timed_operation
from app.models.user import User
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard_service import get_dashboard

logger = logging.getLogger(__name__)
router = APIRouter(tags=["dashboard"])


@router.get("/businesses/{business_id}/dashboard", response_model=DashboardResponse)
def business_dashboard(
    business_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        with timed_operation(logger, "dashboard", business_id=business_id):
            return get_dashboard(db, business_id, current_user.id)
    except BusinessNotFoundError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
