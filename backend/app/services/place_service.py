import re
import uuid
from urllib.parse import unquote

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.models.business import Business


def parse_place_id_from_url(google_maps_url: str) -> str | None:
    """Extract a place ID from common Google Maps URL formats."""
    patterns = [
        r"place_id[=:]([A-Za-z0-9_-]+)",
        r"/place/[^/]+/@[^/]+/data=.*!1s(0x[0-9a-f]+:[0-9a-fx]+)",
        r"!1s(ChIJ[A-Za-z0-9_-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, google_maps_url)
        if match:
            return match.group(1)
    return None


def _extract_name_from_url(google_maps_url: str) -> str | None:
    """Try to pull a human-readable business name from the Maps URL path."""
    match = re.search(r"/place/([^/@]+)", google_maps_url)
    if match:
        raw = unquote(match.group(1))
        return raw.replace("+", " ")
    return None


async def resolve_place_details(
    place_id: str, google_maps_url: str | None = None
) -> dict:
    """Fetch place name and address from Google Places API.

    Falls back to name extracted from URL, or a placeholder.
    """
    if not settings.GOOGLE_PLACES_API_KEY:
        name = None
        if google_maps_url:
            name = _extract_name_from_url(google_maps_url)
        return {
            "name": name or f"Business ({place_id[:12]}...)",
            "address": None,
        }

    url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "fields": "name,formatted_address",
        "key": settings.GOOGLE_PLACES_API_KEY,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        result = resp.json().get("result", {})

    return {
        "name": result.get("name", "Unknown Business"),
        "address": result.get("formatted_address"),
    }


async def get_or_create_business(
    db: Session,
    place_id: str,
    user_id: uuid.UUID,
    google_maps_url: str | None = None,
    business_type: str = "other",
) -> Business:
    """Return existing business owned by this user, or create a new one."""
    existing = (
        db.query(Business)
        .filter(Business.place_id == place_id, Business.user_id == user_id)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail="You have already added this business.",
        )

    details = await resolve_place_details(place_id, google_maps_url)
    business = Business(
        id=uuid.uuid4(),
        user_id=user_id,
        place_id=place_id,
        name=details["name"],
        business_type=business_type,
        address=details["address"],
        google_maps_url=google_maps_url,
    )
    db.add(business)
    db.commit()
    db.refresh(business)
    return business
