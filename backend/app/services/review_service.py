import logging
import uuid

from sqlalchemy.orm import Session

from app.logging_config import timed_operation
from app.models.analysis import Analysis
from app.models.business import Business
from app.models.review import Review
from app.providers import get_review_provider

logger = logging.getLogger(__name__)

MAX_REVIEWS_PER_FETCH = 500


def fetch_reviews_for_business(db: Session, business: Business) -> list[Review]:
    """Fetch reviews via the configured provider, replacing all existing reviews.

    Old reviews and stale analysis are deleted so the business always
    reflects a single, consistent, up-to-date review set.
    """
    provider = get_review_provider()

    with timed_operation(logger, "provider_fetch", business_id=business.id, provider=type(provider).__name__):
        raw_reviews = provider.fetch_reviews(business.place_id, business.google_maps_url)

    if len(raw_reviews) > MAX_REVIEWS_PER_FETCH:
        logger.warning(
            "op=provider_fetch business_id=%s review_count=%d truncated_to=%d",
            business.id, len(raw_reviews), MAX_REVIEWS_PER_FETCH,
        )
        raw_reviews = raw_reviews[:MAX_REVIEWS_PER_FETCH]

    deleted_reviews = db.query(Review).filter(Review.business_id == business.id).delete()
    deleted_analyses = db.query(Analysis).filter(Analysis.business_id == business.id).delete()
    if deleted_reviews or deleted_analyses:
        logger.info(
            "op=refresh_clear business_id=%s old_reviews_deleted=%d old_analyses_deleted=%d",
            business.id, deleted_reviews, deleted_analyses,
        )

    for raw in raw_reviews:
        db.add(Review(
            id=uuid.uuid4(),
            business_id=business.id,
            external_id=raw["external_id"],
            source=raw["source"],
            author=raw.get("author"),
            rating=raw["rating"],
            text=raw.get("text"),
            published_at=raw.get("published_at"),
        ))

    db.flush()
    _update_business_stats(business, len(raw_reviews), raw_reviews)
    db.commit()

    return (
        db.query(Review)
        .filter(Review.business_id == business.id)
        .order_by(Review.published_at.desc())
        .all()
    )


def _update_business_stats(
    business: Business, total: int, raw_reviews: list[dict]
) -> None:
    if total == 0:
        business.total_reviews = 0
        business.avg_rating = None
        return
    avg = sum(r["rating"] for r in raw_reviews) / total
    business.total_reviews = total
    business.avg_rating = round(avg, 2)
