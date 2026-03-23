"""Offline sandbox: browse manifest catalog and import sample businesses into the current user's account."""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models.business import Business
from app.models.competitor_link import CompetitorLink
from app.models.user import User
from app.schemas.business import BusinessRead
from app.schemas.sandbox import (
    CatalogBusiness,
    CatalogResponse,
    CatalogScenario,
    SandboxImport,
    SandboxResetResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sandbox", tags=["sandbox"])

_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "offline"


def _offline_only() -> None:
    if settings.REVIEW_PROVIDER != "offline":
        raise HTTPException(
            status_code=404, detail="Sandbox is only available when REVIEW_PROVIDER=offline."
        )


def _load_manifest_raw() -> dict:
    path = _DATA_DIR / "manifest.json"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _manifest_business_map(manifest: dict) -> dict[str, dict]:
    return {b["place_id"]: b for b in manifest.get("businesses", [])}


def _review_count_for_entry(entry: dict) -> int:
    rel = entry.get("reviews_file")
    if not rel:
        return 0
    fp = _DATA_DIR / rel
    if not fp.exists():
        return 0
    try:
        with open(fp, encoding="utf-8") as f:
            data = json.load(f)
        return len(data) if isinstance(data, list) else 0
    except (json.JSONDecodeError, OSError):
        return 0


def _scenario_place_ids(manifest: dict) -> set[str]:
    ids: set[str] = set()
    for scenario in manifest.get("scenarios", {}).values():
        ids.add(scenario["main"])
        ids.update(scenario.get("competitors", []))
    return ids


def _user_business_by_place(db: Session, user_id: uuid.UUID) -> dict[str, Business]:
    rows = db.query(Business).filter(Business.user_id == user_id).all()
    return {b.place_id: b for b in rows}


def _to_catalog_business(
    entry: dict,
    review_count: int,
    user_map: dict[str, Business],
) -> CatalogBusiness:
    b = user_map.get(entry["place_id"])
    return CatalogBusiness(
        place_id=entry["place_id"],
        name=entry["name"],
        business_type=entry.get("business_type", "other"),
        address=entry.get("address"),
        review_count=review_count,
        imported=b is not None,
        business_id=b.id if b else None,
    )


@router.get("/catalog", response_model=CatalogResponse)
def get_catalog(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _offline_only()
    manifest = _load_manifest_raw()
    if not manifest.get("businesses"):
        raise HTTPException(status_code=500, detail="Offline manifest is missing or empty.")

    by_place = _manifest_business_map(manifest)
    user_map = _user_business_by_place(db, current_user.id)
    scenario_ids = _scenario_place_ids(manifest)

    # Precompute review counts per place_id
    review_counts: dict[str, int] = {}
    for pid, entry in by_place.items():
        review_counts[pid] = _review_count_for_entry(entry)

    scenarios_out: list[CatalogScenario] = []
    for sid, scenario in manifest.get("scenarios", {}).items():
        main_pid = scenario["main"]
        main_entry = by_place.get(main_pid)
        if not main_entry:
            continue
        main_cb = _to_catalog_business(main_entry, review_counts.get(main_pid, 0), user_map)
        comp_cbs: list[CatalogBusiness] = []
        for cpid in scenario.get("competitors", []):
            ce = by_place.get(cpid)
            if ce:
                comp_cbs.append(_to_catalog_business(ce, review_counts.get(cpid, 0), user_map))
        scenarios_out.append(
            CatalogScenario(
                id=sid,
                description=scenario.get("description", ""),
                main=main_cb,
                competitors=comp_cbs,
            )
        )

    standalone: list[CatalogBusiness] = []
    for pid, entry in by_place.items():
        if pid not in scenario_ids:
            standalone.append(_to_catalog_business(entry, review_counts.get(pid, 0), user_map))

    return CatalogResponse(scenarios=scenarios_out, standalone=standalone)


# Match competitors router
MAX_COMPETITORS = 3


@router.post("/import", response_model=BusinessRead, status_code=201)
def import_sample(
    payload: SandboxImport,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _offline_only()
    manifest = _load_manifest_raw()
    by_place = _manifest_business_map(manifest)
    entry = by_place.get(payload.place_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Unknown offline place_id.")

    as_competitor = payload.as_competitor_for is not None

    if payload.as_competitor_for is not None:
        target = (
            db.query(Business)
            .filter(
                Business.id == payload.as_competitor_for,
                Business.user_id == current_user.id,
            )
            .first()
        )
        if not target:
            raise HTTPException(status_code=404, detail="Target business not found.")
        if target.place_id == payload.place_id:
            raise HTTPException(
                status_code=400,
                detail="Cannot add a business as its own competitor.",
            )
        existing_count = (
            db.query(CompetitorLink).filter(CompetitorLink.target_business_id == target.id).count()
        )
        if existing_count >= MAX_COMPETITORS:
            raise HTTPException(
                status_code=400,
                detail=f"Maximum {MAX_COMPETITORS} competitors allowed. Remove one to add another.",
            )

    existing = (
        db.query(Business)
        .filter(
            Business.place_id == payload.place_id,
            Business.user_id == current_user.id,
        )
        .first()
    )

    if existing:
        business = existing
    else:
        business = Business(
            id=uuid.uuid4(),
            user_id=current_user.id,
            place_id=payload.place_id,
            name=entry["name"],
            business_type=entry.get("business_type", "other"),
            address=entry.get("address"),
            google_maps_url=None,
            is_competitor=as_competitor,
        )
        db.add(business)
        db.commit()
        db.refresh(business)
        logger.info(
            "op=sandbox_import user_id=%s place_id=%s as_competitor=%s",
            current_user.id,
            payload.place_id,
            as_competitor,
        )

    if payload.as_competitor_for is not None:
        target_id = payload.as_competitor_for
        link_exists = (
            db.query(CompetitorLink)
            .filter(
                CompetitorLink.target_business_id == target_id,
                CompetitorLink.competitor_business_id == business.id,
            )
            .first()
        )
        if not link_exists:
            link = CompetitorLink(
                target_business_id=target_id,
                competitor_business_id=business.id,
            )
            db.add(link)
            db.commit()
            db.refresh(business)

    return business


@router.post("/reset", response_model=SandboxResetResponse)
def reset_sandbox(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _offline_only()
    to_delete = (
        db.query(Business)
        .filter(
            Business.user_id == current_user.id,
            Business.place_id.startswith("offline_"),
        )
        .all()
    )
    n = len(to_delete)
    for b in to_delete:
        db.delete(b)
    db.commit()
    logger.info("op=sandbox_reset user_id=%s deleted=%d", current_user.id, n)
    return SandboxResetResponse(deleted=n)
