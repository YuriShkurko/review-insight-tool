"""Living demo world tick worker.

Each run computes how many new reviews to inject (sine-wave schedule),
picks templates from the bank weighted by current sentiment, inserts
them into sim_reviews, then calls fetch-reviews + analyze so the
dashboard reflects the new state.

Wave per business (stateless — computed from wall-clock unix time):
  reviews_this_tick = max(0, round(baseline + amplitude * sin(2pi*t/period + phase)))
  sentiment = sin(2pi*t/period + phase)   -- shifts rating mean up/down

Usage:
    DATABASE_URL=... DEMO_API_URL=http://... python scripts/tick_demo.py
    DATABASE_URL=... DEMO_API_URL=http://... python scripts/tick_demo.py --dry-run

Run every 20-30 minutes via cron or ECS scheduled task.
"""

from __future__ import annotations

import argparse
import math
import os
import random
import sys
import uuid
from datetime import UTC, datetime

import httpx

BASE_URL = os.environ.get("DEMO_API_URL", "http://localhost:8000")
DEMO_EMAIL = "demo@review-insight.app"
DEMO_PASSWORD = "DemoWorld2026!"

# ---------------------------------------------------------------------------
# Wave parameters — one entry per business
# period=86400 = one full cycle per day; phases spread businesses apart
# ---------------------------------------------------------------------------

WAVE_PARAMS: dict[str, dict] = {
    "sim_lager_ale_tlv": {
        "baseline": 2.0,
        "amplitude": 1.8,
        "period": 86400,
        "phase": 0.0,
        "rating_mean": 4.3,
        "rating_std": 0.7,
    },
    "sim_beer_garden": {
        "baseline": 1.5,
        "amplitude": 1.2,
        "period": 86400,
        "phase": math.pi / 3,        # ~4 h behind hero peak
        "rating_mean": 3.9,
        "rating_std": 0.9,
    },
    "sim_tap_room": {
        "baseline": 1.5,
        "amplitude": 1.4,
        "period": 86400,
        "phase": 2 * math.pi / 3,   # ~8 h behind hero peak
        "rating_mean": 4.1,
        "rating_std": 0.8,
    },
}

# ---------------------------------------------------------------------------
# Template bank — 40 reviews per business, mixed ratings
# Tick worker samples from rating-appropriate templates so text matches stars.
# ---------------------------------------------------------------------------

TEMPLATES: dict[str, list[dict]] = {
    "sim_lager_ale_tlv": [
        # 5-star
        {"author": "Dor Avni", "rating": 5, "text": "Incredible tap list, something new every visit. The double IPA right now is world class."},
        {"author": "Noa Eitan", "rating": 5, "text": "Best bar on Rothschild, no contest. Knowledgeable staff and rotating craft options."},
        {"author": "Yarden Cohen", "rating": 5, "text": "Came for one beer, stayed for three. The seasonal sour was outstanding."},
        {"author": "Shai Biton", "rating": 5, "text": "Live jazz on Friday + that porter = perfect evening. Will return weekly."},
        {"author": "Gal Peretz", "rating": 5, "text": "My friends think I work here because I keep recommending it. The stout is life-changing."},
        {"author": "Tamar Levy", "rating": 5, "text": "The cheese board and the Belgian wheat are a match made in heaven. Flawless experience."},
        {"author": "Adi Ben-Shahar", "rating": 5, "text": "Quiet Monday evening, bartender talked me through six taps. Left knowing a lot more about beer."},
        {"author": "Ran Ofer", "rating": 5, "text": "Outdoor seating on a warm evening with a cold craft lager. Tel Aviv at its finest."},
        {"author": "Michal Saar", "rating": 5, "text": "The sampler board is the move for a first visit. Five styles, all excellent, good value."},
        {"author": "Omer Katz", "rating": 5, "text": "Happy hour deals on weekdays are genuinely good. The pale ale hits different at half price."},
        # 4-star
        {"author": "Dana Freed", "rating": 4, "text": "Great spot, gets crowded on weekends but the quality is consistent. Love the rotating taps."},
        {"author": "Itai Gold", "rating": 4, "text": "Solid bar with real personality. The porter is my regular order. Seating gets tight by 9pm."},
        {"author": "Liron Ben-Zvi", "rating": 4, "text": "Industrial design and long bar are a vibe. Service is fast even when full."},
        {"author": "Ofer Mizrahi", "rating": 4, "text": "Good selection, friendly staff. Slightly pricey but you're paying for curation."},
        {"author": "Ayelet Ron", "rating": 4, "text": "Love the concept — always something on tap I haven't tried. Wish they did more food."},
        {"author": "Nadav Shapiro", "rating": 4, "text": "Great discovery. The flight of four is perfect for exploring without committing to a pint."},
        # 3-star
        {"author": "Ilan Gross", "rating": 3, "text": "Good beer, slow service on a busy night. Had to flag someone down twice."},
        {"author": "Tali Sela", "rating": 3, "text": "Nice place but quite loud. Hard to hold a conversation at peak hours."},
        {"author": "Benny Har", "rating": 3, "text": "Decent selection, nothing extraordinary. Prices are on the high side for the area."},
        {"author": "Keren Ziv", "rating": 3, "text": "Waited 15 minutes for a drink on a Friday. Beer was worth it but the wait was frustrating."},
        # 2-star
        {"author": "Rami Dor", "rating": 2, "text": "Too crowded and too loud. Had to shout to order. Beer was fine but the experience wasn't."},
        {"author": "Sigal Har-Lev", "rating": 2, "text": "Service felt dismissive. My beer arrived warm and it took forever to get someone's attention."},
        # 1-star
        {"author": "Mor Tzur", "rating": 1, "text": "Waited 25 minutes, never got served. Left and went somewhere else. Won't be back."},
    ],
    "sim_beer_garden": [
        # 5-star
        {"author": "Yuval Paz", "rating": 5, "text": "The garden at sunset is something else. Cold lager, fairy lights, zero stress."},
        {"author": "Shir Blum", "rating": 5, "text": "Best outdoor bar in the city. We come every Sunday — the brunch + beer combo is a ritual now."},
        {"author": "Avi Stern", "rating": 5, "text": "Magical atmosphere on a warm night. Staff are genuinely friendly and the garden is immaculate."},
        {"author": "Hila Ohayon", "rating": 5, "text": "Took my team here for a celebration. Big tables, great service, everyone was happy."},
        {"author": "Kobi Levi", "rating": 5, "text": "The cider is a hidden gem here. Garden is well maintained and vibe is just right."},
        {"author": "Nurit Ben-David", "rating": 5, "text": "Perfect for a first date — beautiful setting, relaxed pace, good drink list."},
        {"author": "Tal Weiss", "rating": 5, "text": "The garden brunch is an institution. Go on a Sunday morning and thank me later."},
        {"author": "Gadi Mor", "rating": 5, "text": "Came on a Tuesday evening — quiet, gorgeous, and the lager was perfectly cold. Love this place."},
        # 4-star
        {"author": "Roni Samson", "rating": 4, "text": "Beautiful outdoor setting. Beer selection is mostly mainstream but the atmosphere makes up for it."},
        {"author": "Inbal Cohen", "rating": 4, "text": "Lovely garden bar. The wheat beer is refreshing and the food is better than expected."},
        {"author": "Yossi Katz", "rating": 4, "text": "Great for groups — big tables and the staff handles crowds well. Wish the tap list were wider."},
        {"author": "Limor Raz", "rating": 4, "text": "Solid neighborhood bar elevated by the outdoor area. The burger + pale ale is the combo."},
        {"author": "Erez Bar", "rating": 4, "text": "Regular haunt for us. Not the most adventurous tap list but reliably good."},
        {"author": "Neta Gold", "rating": 4, "text": "The garden in the evening is beautiful. Service is friendly if a little slow."},
        # 3-star
        {"author": "Dina Koren", "rating": 3, "text": "Pretty place but the beer selection is limited to mainstream brands. Go for the atmosphere."},
        {"author": "Amos Tzur", "rating": 3, "text": "Service is inconsistent — sometimes fast, sometimes you're waiting forever. Nice garden though."},
        {"author": "Yael Gross", "rating": 3, "text": "Nice on a weekday. Packed and hard to find a seat on weekends."},
        {"author": "Boaz Ofer", "rating": 3, "text": "Overpriced for what it is. You're paying for the garden, not the beer quality."},
        # 2-star
        {"author": "Sari Ben-Zion", "rating": 2, "text": "Beer arrived warm twice. Beautiful space but execution needs work."},
        {"author": "Ran Blum", "rating": 2, "text": "Expected more given the reputation. Noisy, cramped on the weekend, and the service was scattered."},
        # 1-star
        {"author": "Dori Azulay", "rating": 1, "text": "Waited 30 minutes, wrong order arrived, never got an apology. Beautiful garden but that's it."},
    ],
    "sim_tap_room": [
        # 5-star
        {"author": "Amir Sagi", "rating": 5, "text": "24 taps, all rotating, all excellent. This is the only craft beer bar that really gets it in Tel Aviv."},
        {"author": "Shani Cohen", "rating": 5, "text": "The barrel-aged stout they had last week was the best beer I've had in years. Staff know their stuff."},
        {"author": "Rafi Levi", "rating": 5, "text": "If you care about craft beer this is your place. They import rare stuff you genuinely can't find elsewhere."},
        {"author": "Dotan Peretz", "rating": 5, "text": "The chalkboard tap list changes constantly. Something new every visit. The DIPA right now is extraordinary."},
        {"author": "Orli Bar", "rating": 5, "text": "Staff recommended a sour I would never have picked myself — it was outstanding. Real expertise here."},
        {"author": "Pini Ben-Haim", "rating": 5, "text": "For beer geeks this is paradise. Flight of four is the move for first-timers."},
        {"author": "Moshe Shaul", "rating": 5, "text": "Raised the bar (pun intended) for craft beer in this city. The session IPA on tap now is brilliant."},
        {"author": "Stav Rosen", "rating": 5, "text": "No shortcuts, just great beer and passion. This is what a craft beer bar should be."},
        {"author": "Inbal Mor", "rating": 5, "text": "The rotating list keeps me coming back weekly. Never the same beer twice, always excellent."},
        {"author": "Yonit Ziv", "rating": 5, "text": "Consistent quality across every visit. The double IPA is exceptional and the staff are genuine experts."},
        # 4-star
        {"author": "Limor Sela", "rating": 4, "text": "Serious craft beer bar. The staff can talk for hours about beer styles. Very knowledgeable."},
        {"author": "Noam Elul", "rating": 4, "text": "Love the chalkboard tap list. Something new every time. The sour this week is amazing."},
        {"author": "Tali Katz", "rating": 4, "text": "Tiny bar but big on quality. Standing room only on Thursdays but worth the squeeze."},
        {"author": "Ronit Shahar", "rating": 4, "text": "Great beer education — staff will help you find exactly what you're looking for."},
        {"author": "Yaron Green", "rating": 4, "text": "The flight of four is a great way to explore. Always discover something new here."},
        {"author": "Gad Cohen", "rating": 4, "text": "Serious about craft in a way most Tel Aviv bars aren't. Pricey but fair for the curation."},
        # 3-star
        {"author": "Anat Friedman", "rating": 3, "text": "The beer is excellent but the bar is small and cramped. Hard to get a seat on weekends."},
        {"author": "Barak Levi", "rating": 3, "text": "Good selection but pricey. You're paying for the curation, which is fair, but still."},
        {"author": "Michal Raz", "rating": 3, "text": "The beer is great but the food menu is very limited. Come for drinks only."},
        {"author": "Omer Klein", "rating": 3, "text": "Amazing tap list, claustrophobic space. Hard to relax when you're shoulder to shoulder."},
        # 2-star
        {"author": "Yoni Bar", "rating": 2, "text": "Too small, too loud, too crowded. The beer is great but the experience isn't worth it on weekends."},
        {"author": "Dana Dagan", "rating": 2, "text": "Waited 20 minutes to order at the bar. No apology, no acknowledgement. Beer was good but still."},
        # 1-star
        {"author": "Ilan Tzur", "rating": 1, "text": "Turned away at the door — 'too full'. Couldn't even see inside. Never tried, never will."},
    ],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def compute_tick(place_id: str, now_ts: float) -> tuple[int, float]:
    """Return (n_reviews, sentiment) for this tick based on wave params."""
    p = WAVE_PARAMS[place_id]
    angle = 2 * math.pi * now_ts / p["period"] + p["phase"]
    sine_val = math.sin(angle)
    n = max(0, round(p["baseline"] + p["amplitude"] * sine_val))
    return n, sine_val


def pick_rating(place_id: str, sentiment: float, rng: random.Random) -> int:
    p = WAVE_PARAMS[place_id]
    mean = p["rating_mean"] + sentiment * 0.6
    raw = rng.gauss(mean, p["rating_std"])
    return max(1, min(5, round(raw)))


def pick_template(place_id: str, rating: int, rng: random.Random, used: set) -> dict | None:
    """Pick an unused template matching the target rating, fallback to adjacent."""
    pool = TEMPLATES[place_id]
    for target in [rating, rating - 1, rating + 1, rating - 2, rating + 2]:
        candidates = [t for t in pool if t["rating"] == target and t["author"] not in used]
        if candidates:
            return rng.choice(candidates)
    return None


def login(client: httpx.Client) -> str:
    r = client.post("/api/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
    r.raise_for_status()
    return r.json()["access_token"]


def get_business_id(client: httpx.Client, headers: dict, place_id: str) -> str | None:
    r = client.get("/api/businesses", headers=headers)
    r.raise_for_status()
    for b in r.json():
        if b["place_id"] == place_id:
            return b["id"]
    return None


def insert_reviews(db_url: str, place_id: str, reviews: list[dict], dry_run: bool) -> int:
    import sqlalchemy as sa

    if dry_run:
        for rev in reviews:
            print(f"    [dry-run] would insert: {rev['author']} ({rev['rating']}*) - {rev['text'][:60]}...")
        return len(reviews)

    engine = sa.create_engine(db_url)
    inserted = 0
    now = datetime.now(UTC)
    with engine.begin() as conn:
        for rev in reviews:
            ext_id = f"tick_{place_id}_{uuid.uuid4().hex[:12]}"
            try:
                conn.execute(
                    sa.text(
                        """
                        INSERT INTO sim_reviews (id, place_id, external_id, author, rating, text, published_at)
                        VALUES (:id, :place_id, :ext_id, :author, :rating, :text, :pub)
                        ON CONFLICT (place_id, external_id) DO NOTHING
                        """
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "place_id": place_id,
                        "ext_id": ext_id,
                        "author": rev["author"],
                        "rating": rev["rating"],
                        "text": rev["text"],
                        "pub": now,
                    },
                )
                inserted += 1
            except Exception as e:
                print(f"    warning: {e}", flush=True)
    return inserted


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Print what would be inserted, don't write")
    args = parser.parse_args()

    db_url = os.environ.get("DATABASE_URL")
    if not db_url and not args.dry_run:
        print("ERROR: DATABASE_URL is required (unless --dry-run)", file=sys.stderr)
        sys.exit(1)

    now_ts = datetime.now(UTC).timestamp()
    rng = random.Random(int(now_ts // 300))  # seed changes every 5 min for variety
    tag = "[dry-run] " if args.dry_run else ""

    print(f"\n{tag}Demo world tick -> {BASE_URL}  ({datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')})", flush=True)

    client = httpx.Client(base_url=BASE_URL, timeout=60)
    token = login(client)
    headers = {"Authorization": f"Bearer {token}"}

    for place_id in WAVE_PARAMS:
        n_reviews, sentiment = compute_tick(place_id, now_ts)
        direction = "up" if sentiment > 0.2 else ("down" if sentiment < -0.2 else "neutral")
        print(f"\n  {place_id}  wave={direction} ({sentiment:+.2f})  reviews_this_tick={n_reviews}", flush=True)

        if n_reviews == 0:
            print("  -> quiet tick, skipping", flush=True)
            continue

        used_authors: set = set()
        batch: list[dict] = []
        for _ in range(n_reviews):
            rating = pick_rating(place_id, sentiment, rng)
            tmpl = pick_template(place_id, rating, rng, used_authors)
            if tmpl is None:
                print("  -> template pool exhausted for this tick", flush=True)
                break
            used_authors.add(tmpl["author"])
            batch.append(tmpl)

        inserted = insert_reviews(db_url or "", place_id, batch, args.dry_run)
        print(f"  -> inserted {inserted} review(s)", flush=True)

        if args.dry_run:
            continue

        biz_id = get_business_id(client, headers, place_id)
        if not biz_id:
            print(f"  -> business not found in API, skipping fetch/analyze", flush=True)
            continue

        r = client.post(f"/api/businesses/{biz_id}/fetch-reviews", headers=headers)
        if r.status_code == 200:
            print(f"  -> fetch-reviews ok", flush=True)
        else:
            print(f"  -> fetch-reviews {r.status_code}: {r.text[:80]}", flush=True)

        r = client.post(f"/api/businesses/{biz_id}/analyze", headers=headers)
        if r.status_code == 200:
            print(f"  -> analyze ok", flush=True)
        else:
            print(f"  -> analyze skipped: {r.status_code} {r.text[:80]}", flush=True)

    print(f"\n{tag}Tick complete.", flush=True)


if __name__ == "__main__":
    main()
