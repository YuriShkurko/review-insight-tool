import uuid

from sqlalchemy.orm import Session

from app.models.business import Business
from app.models.review import Review
from app.providers import get_review_provider


def fetch_reviews_for_business(db: Session, business: Business) -> list[Review]:
    """Fetch reviews via the configured provider and persist new ones.

    Uses external_id to deduplicate -- repeated calls are safe and will only
    insert reviews that don't already exist for this business.
    """
    provider = get_review_provider()
    raw_reviews = provider.fetch_reviews(business.place_id, business.google_maps_url)

    existing_ids = {
        eid
        for (eid,) in db.query(Review.external_id)
        .filter(Review.business_id == business.id)
        .all()
    }

    new_reviews = []
    for raw in raw_reviews:
        if raw["external_id"] in existing_ids:
            continue
        review = Review(
            id=uuid.uuid4(),
            business_id=business.id,
            external_id=raw["external_id"],
            source=raw["source"],
            author=raw.get("author"),
            rating=raw["rating"],
            text=raw.get("text"),
            published_at=raw.get("published_at"),
        )
        db.add(review)
        new_reviews.append(review)

    if new_reviews:
        db.flush()
        _update_business_stats(db, business)

    db.commit()

    return (
        db.query(Review)
        .filter(Review.business_id == business.id)
        .order_by(Review.published_at.desc())
        .all()
    )


def _update_business_stats(db: Session, business: Business) -> None:
    reviews = db.query(Review).filter(Review.business_id == business.id).all()
    if not reviews:
        return
    total = len(reviews)
    avg = sum(r.rating for r in reviews) / total
    business.total_reviews = total
    business.avg_rating = round(avg, 2)
