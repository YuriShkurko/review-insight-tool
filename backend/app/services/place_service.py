import contextlib
import logging
import re
import uuid
from urllib.parse import unquote

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.errors import BusinessAlreadyExistsError
from app.models.business import Business

logger = logging.getLogger(__name__)

_SHORTLINK_HOSTS = {"maps.app.goo.gl", "goo.gl"}
_REDIRECT_TIMEOUT = 10

# Place ID extraction patterns (order matters: more specific first).
# Supports: place_id=, query_place_id=, /place/.../data=!...!1s0x... or !1sChIJ..., and bare !1s forms.
_PLACE_ID_PATTERNS = [
    # Query params (most reliable when present)
    r"[?&]place_id=([A-Za-z0-9_-]+)",
    r"[?&]query_place_id=([A-Za-z0-9_-]+)",
    # Legacy style place_id: value (no query)
    r"place_id[=:]([A-Za-z0-9_-]+)",
    # /place/Name/@lat,lng,zoom/data=!3m1!...!1s0xHEX:0xHEX or !1sChIJ...
    r"/place/[^/]+/@[^/]+/data=[^#]*!1s(0x[0-9a-fA-F]+:0x[0-9a-fA-F]+)",
    r"/place/[^/]+/@[^/]+/data=[^#]*!1s(ChIJ[A-Za-z0-9_-]+)",
    # Embedded in path or data blob (ChIJ format)
    r"!1s(ChIJ[A-Za-z0-9_-]+)",
    # Hex format anywhere in URL (e.g. after redirect)
    r"!1s(0x[0-9a-fA-F]+:0x[0-9a-fA-F]+)",
    # Fallback: ChIJ segment in path (e.g. /place/Name/ChIJ...)
    r"(?:^|/)(ChIJ[A-Za-z0-9_-]{20,})(?:[?/]|$)",
]


def _normalize_url_for_parsing(url: str) -> str:
    """Strip whitespace, decode percent-encoding, and drop fragment for robust parsing."""
    if not url or not isinstance(url, str):
        return ""
    s = url.strip()
    with contextlib.suppress(ValueError, TypeError):
        s = unquote(s)
    if "#" in s:
        s = s.split("#", 1)[0]
    return s


def _is_shortened_url(url: str) -> bool:
    """Check if a URL is a known Google Maps shortened link."""
    return any(host in url for host in _SHORTLINK_HOSTS)


async def _resolve_shortened_url(url: str) -> str | None:
    """Follow redirects on a shortened Google Maps URL and return the final URL.
    Tries HEAD first; falls back to GET if the server does not redirect on HEAD.
    """
    try:
        async with httpx.AsyncClient(
            timeout=_REDIRECT_TIMEOUT, follow_redirects=True, max_redirects=5
        ) as client:
            # Some servers don't redirect on HEAD; try GET if HEAD yields same host
            resp = await client.head(url)
            resolved = str(resp.url)
            if _is_shortened_url(resolved):
                resp_get = await client.get(url)
                resolved = str(resp_get.url)
            logger.info("op=resolve_shortlink success=true resolved=%s", resolved)
            return resolved
    except Exception as exc:
        logger.warning(
            "op=resolve_shortlink success=false error=%s detail=%s",
            type(exc).__name__,
            exc,
        )
        return None


def parse_place_id_from_url(google_maps_url: str) -> str | None:
    """Extract a place ID from common Google Maps URL formats.

    Supports: place_id= / query_place_id= params, google.com/maps/place/.../data=!...!1s...,
    maps.app.goo.gl (after resolve), and URLs with extra query/fragment.
    Returns None if no known format is found.
    """
    url = _normalize_url_for_parsing(google_maps_url)
    if not url:
        return None
    for pattern in _PLACE_ID_PATTERNS:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


async def resolve_place_id_from_url(google_maps_url: str) -> tuple[str | None, str]:
    """Parse a place ID from a Google Maps URL, resolving shortened links first.

    Returns (place_id, resolved_url). If the URL was shortened, resolved_url is the
    final URL after redirects; otherwise it is the normalized input.
    Fails gracefully: returns (None, url) when no place ID can be extracted.
    """
    url = (google_maps_url or "").strip()
    if not url:
        return None, url
    if _is_shortened_url(url):
        resolved = await _resolve_shortened_url(url)
        if resolved:
            url = resolved
    place_id = parse_place_id_from_url(url)
    return place_id, url


def _extract_name_from_url(google_maps_url: str) -> str | None:
    """Try to pull a human-readable business name from the Maps URL path."""
    match = re.search(r"/place/([^/@]+)", google_maps_url)
    if match:
        raw = unquote(match.group(1))
        return raw.replace("+", " ")
    return None


async def resolve_place_details(place_id: str, google_maps_url: str | None = None) -> dict:
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
    """Return existing business owned by this user, or create a new one.

    If the business exists as competitor-only, promote it to a regular business.
    Raises 409 if the business already exists as a regular (non-competitor) business.
    """
    existing = (
        db.query(Business)
        .filter(Business.place_id == place_id, Business.user_id == user_id)
        .first()
    )
    if existing:
        if existing.is_competitor:
            existing.is_competitor = False
            db.commit()
            db.refresh(existing)
            return existing
        raise BusinessAlreadyExistsError()

    details = await resolve_place_details(place_id, google_maps_url)
    business = Business(
        id=uuid.uuid4(),
        user_id=user_id,
        place_id=place_id,
        name=details["name"],
        business_type=business_type,
        address=details["address"],
        google_maps_url=google_maps_url,
        is_competitor=False,
    )
    db.add(business)
    db.commit()
    db.refresh(business)
    return business


async def get_or_create_business_for_competitor(
    db: Session,
    place_id: str,
    user_id: uuid.UUID,
    google_maps_url: str | None = None,
    business_type: str = "other",
) -> Business:
    """Return existing business (same user + place_id) or create a new one marked as competitor. Never raises 409."""
    existing = (
        db.query(Business)
        .filter(Business.place_id == place_id, Business.user_id == user_id)
        .first()
    )
    if existing:
        return existing

    details = await resolve_place_details(place_id, google_maps_url)
    business = Business(
        id=uuid.uuid4(),
        user_id=user_id,
        place_id=place_id,
        name=details["name"],
        business_type=business_type,
        address=details["address"],
        google_maps_url=google_maps_url,
        is_competitor=True,
    )
    db.add(business)
    db.commit()
    db.refresh(business)
    return business
