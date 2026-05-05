import logging
import uuid

from sqlalchemy.orm import Session

from app.logging_config import timed_operation
from app.models.analysis import Analysis
from app.models.business import Business
from app.models.review import Review
from app.observability import reviews_fetched
from app.providers import get_review_provider

logger = logging.getLogger(__name__)

MAX_REVIEWS_PER_FETCH = 500
UNCAPPED_PROVIDER_NAMES = {"SimulationProvider"}


def fetch_reviews_for_business(db: Session, business: Business) -> list[Review]:
    """Fetch reviews via the configured provider, replacing all existing reviews.

    Old reviews and stale analysis are deleted so the business always
    reflects a single, consistent, up-to-date review set.
    """
    provider = get_review_provider()

    with timed_operation(
        logger, "provider_fetch", business_id=business.id, provider=type(provider).__name__
    ):
        raw_reviews = provider.fetch_reviews(business.place_id, business.google_maps_url)

    # Archive raw provider response to MongoDB (fire-and-forget)
    raw_body = getattr(provider, "last_raw_response", None)
    if raw_body is not None:
        from app.mongo import store_raw_provider_response

        store_raw_provider_response(
            business_id=str(business.id),
            provider=type(provider).__name__.lower().replace("provider", ""),
            place_id=business.place_id,
            raw_response=raw_body,
            review_count=len(raw_reviews),
        )

    reviews_fetched.add(len(raw_reviews))

    provider_name = type(provider).__name__
    if len(raw_reviews) > MAX_REVIEWS_PER_FETCH and provider_name not in UNCAPPED_PROVIDER_NAMES:
        logger.warning(
            "op=provider_fetch business_id=%s review_count=%d truncated_to=%d",
            business.id,
            len(raw_reviews),
            MAX_REVIEWS_PER_FETCH,
        )
        raw_reviews = raw_reviews[:MAX_REVIEWS_PER_FETCH]

    # Refuse to wipe existing reviews when the provider returned nothing.
    # Sim/offline place_ids (sim_* / offline_*) must never lose data due to a
    # missing manifest entry or transient provider failure.
    if len(raw_reviews) == 0:
        existing_count = db.query(Review).filter(Review.business_id == business.id).count()
        if existing_count > 0:
            logger.warning(
                "op=refresh_abort business_id=%s place_id=%s reason=provider_returned_zero "
                "existing_reviews=%d — skipping delete to protect existing data",
                business.id,
                business.place_id,
                existing_count,
            )
            return (
                db.query(Review)
                .filter(Review.business_id == business.id)
                .order_by(Review.published_at.desc())
                .all()
            )

    deleted_reviews = db.query(Review).filter(Review.business_id == business.id).delete()
    deleted_analyses = db.query(Analysis).filter(Analysis.business_id == business.id).delete()
    if deleted_reviews or deleted_analyses:
        logger.info(
            "op=refresh_clear business_id=%s old_reviews_deleted=%d old_analyses_deleted=%d",
            business.id,
            deleted_reviews,
            deleted_analyses,
        )

    for raw in raw_reviews:
        db.add(
            Review(
                id=uuid.uuid4(),
                business_id=business.id,
                external_id=raw["external_id"],
                source=raw["source"],
                author=raw.get("author"),
                rating=raw["rating"],
                text=raw.get("text"),
                published_at=raw.get("published_at"),
            )
        )

    db.flush()
    _update_business_stats(business, len(raw_reviews), raw_reviews)
    db.commit()

    return (
        db.query(Review)
        .filter(Review.business_id == business.id)
        .order_by(Review.published_at.desc())
        .all()
    )


def _update_business_stats(business: Business, total: int, raw_reviews: list[dict]) -> None:
    if total == 0:
        business.total_reviews = 0
        business.avg_rating = None
        return
    avg = sum(r["rating"] for r in raw_reviews) / total
    business.total_reviews = total
    business.avg_rating = round(avg, 2)
