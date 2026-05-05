import uuid
from datetime import UTC, datetime, timedelta

from app.models.business import Business
from app.models.user import User
from app.services import review_service
from app.services.review_service import fetch_reviews_for_business


class _Provider:
    def __init__(self, count: int):
        self.count = count

    def fetch_reviews(self, place_id: str, google_maps_url: str | None = None) -> list[dict]:
        now = datetime.now(UTC)
        return [
            {
                "external_id": f"review-{i}",
                "source": "test",
                "author": f"Author {i}",
                "rating": 5 if i % 2 == 0 else 4,
                "text": f"Review {i}",
                "published_at": now - timedelta(minutes=i),
            }
            for i in range(self.count)
        ]


class SimulationProvider(_Provider):
    pass


def _business(db_session, place_id: str) -> Business:
    user = User(id=uuid.uuid4(), email=f"{place_id}@example.test", hashed_password="x")
    db_session.add(user)
    db_session.flush()
    return Business(
        id=uuid.uuid4(),
        user_id=user.id,
        place_id=place_id,
        name="Demo",
        business_type="bar",
        total_reviews=0,
    )


def test_fetch_reviews_caps_non_simulation_provider(db_session, monkeypatch):
    monkeypatch.setattr(review_service, "get_review_provider", lambda: _Provider(550))
    business = _business(db_session, "regular_place")
    db_session.add(business)
    db_session.commit()

    reviews = fetch_reviews_for_business(db_session, business)

    assert len(reviews) == review_service.MAX_REVIEWS_PER_FETCH
    assert business.total_reviews == review_service.MAX_REVIEWS_PER_FETCH


def test_fetch_reviews_does_not_cap_simulation_provider(db_session, monkeypatch):
    monkeypatch.setattr(review_service, "get_review_provider", lambda: SimulationProvider(550))
    business = _business(db_session, "sim_tap_room")
    db_session.add(business)
    db_session.commit()

    reviews = fetch_reviews_for_business(db_session, business)

    assert len(reviews) == 550
    assert business.total_reviews == 550
