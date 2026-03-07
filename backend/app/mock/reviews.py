"""Realistic mock review data for development without API keys."""

import hashlib
import random
from datetime import datetime, timedelta, timezone

_POSITIVE_REVIEWS = [
    {
        "author": "Sarah M.",
        "rating": 5,
        "text": "Absolutely love this place! The staff is incredibly friendly and the atmosphere is perfect for both working and hanging out. Will definitely be back.",
    },
    {
        "author": "James K.",
        "rating": 5,
        "text": "Best experience I've had in a long time. Everything was top-notch from start to finish. Highly recommend to anyone looking for quality service.",
    },
    {
        "author": "Emily R.",
        "rating": 4,
        "text": "Really great spot. The coffee is excellent and the pastries are fresh every morning. Only minor issue is seating can be limited during peak hours.",
    },
    {
        "author": "David L.",
        "rating": 5,
        "text": "The attention to detail here is remarkable. You can tell the owners genuinely care about creating a great experience for their customers.",
    },
    {
        "author": "Maria G.",
        "rating": 4,
        "text": "Great value for money. The portions are generous and everything tastes homemade. The outdoor seating area is a nice touch.",
    },
    {
        "author": "Alex T.",
        "rating": 5,
        "text": "I've been coming here weekly for six months now and the quality has never dipped. Consistent excellence is rare and I appreciate it.",
    },
    {
        "author": "Rachel W.",
        "rating": 4,
        "text": "Clean, well-organized, and the staff always remembers my order. It's the small things that make a place stand out.",
    },
]

_NEGATIVE_REVIEWS = [
    {
        "author": "Mike P.",
        "rating": 2,
        "text": "Waited 30 minutes for a simple order. The food was okay when it finally arrived but the wait time is unacceptable during a weekday lunch.",
    },
    {
        "author": "Karen S.",
        "rating": 1,
        "text": "Very disappointing experience. The place was dirty, the service was rude, and my order was wrong. Will not be returning.",
    },
    {
        "author": "Tom H.",
        "rating": 2,
        "text": "Used to be much better. Quality has gone downhill in the last few months. Portions are smaller and prices have gone up significantly.",
    },
    {
        "author": "Lisa N.",
        "rating": 2,
        "text": "Parking is a nightmare and the noise level inside makes it impossible to have a conversation. Food is mediocre at best.",
    },
]

_MIXED_REVIEWS = [
    {
        "author": "Chris B.",
        "rating": 3,
        "text": "Decent place overall. Nothing spectacular but nothing terrible either. The menu could use more variety though.",
    },
    {
        "author": "Nicole F.",
        "rating": 3,
        "text": "Hit or miss depending on when you go. Weekend mornings are great, weekday evenings are understaffed and slow.",
    },
    {
        "author": "Jordan D.",
        "rating": 3,
        "text": "The ambiance is nice and the location is convenient, but the food quality doesn't quite match the prices they charge.",
    },
    {
        "author": "Pat O.",
        "rating": 3,
        "text": "Solid 3 stars. Good enough to visit occasionally but not a regular destination. Service is friendly but forgetful.",
    },
]

_ALL_REVIEWS = _POSITIVE_REVIEWS + _NEGATIVE_REVIEWS + _MIXED_REVIEWS


def generate_mock_reviews(place_id: str, count: int = 15) -> list[dict]:
    """Generate deterministic mock reviews seeded by place_id.

    Uses a hash-based seed so the same place_id always produces the same
    set of reviews. Each review gets a stable external_id for deduplication.
    """
    seed = int(hashlib.md5(place_id.encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)

    selected = rng.choices(_ALL_REVIEWS, k=count)
    base_date = datetime(2025, 6, 1, tzinfo=timezone.utc)

    reviews = []
    for i, review in enumerate(selected):
        days_ago = rng.randint(1, 365)
        external_id = hashlib.sha256(f"{place_id}:{i}".encode()).hexdigest()[:16]
        reviews.append(
            {
                "external_id": f"mock_{external_id}",
                "source": "mock",
                "author": review["author"],
                "rating": review["rating"],
                "text": review["text"],
                "published_at": base_date - timedelta(days=days_ago),
            }
        )

    return reviews
