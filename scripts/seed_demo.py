"""Seed the living demo world.

Creates a shared demo account, three businesses (one hero + two competitors),
inserts template reviews into sim_reviews, then calls the live API to run
analysis and comparison so the dashboard is fully populated on first login.

Usage:
    DEMO_API_URL=http://localhost:8000 python scripts/seed_demo.py
    DEMO_API_URL=http://review-insight-alb-xxx.eu-central-1.elb.amazonaws.com python scripts/seed_demo.py

Safe to re-run: skips steps that are already done (idempotent).
"""

import os
import sys

import httpx

BASE_URL = os.environ.get("DEMO_API_URL", "http://localhost:8000")
DEMO_EMAIL = "demo@review-insight.app"
DEMO_PASSWORD = "DemoWorld2026!"

# ---------------------------------------------------------------------------
# Demo businesses
# ---------------------------------------------------------------------------

BUSINESSES = [
    {
        "place_id": "sim_lager_ale_tlv",
        "name": "Lager & Ale TLV",
        "business_type": "bar",
        "address": "Rothschild Blvd 22, Tel Aviv",
        "role": "hero",
    },
    {
        "place_id": "sim_beer_garden",
        "name": "The Beer Garden",
        "business_type": "bar",
        "address": "HaYarkon St 98, Tel Aviv",
        "role": "competitor",
    },
    {
        "place_id": "sim_tap_room",
        "name": "The Tap Room",
        "business_type": "bar",
        "address": "Dizengoff St 55, Tel Aviv",
        "role": "competitor",
    },
]

# ---------------------------------------------------------------------------
# Template reviews — 20 per business
# ---------------------------------------------------------------------------

REVIEWS: dict[str, list[dict]] = {
    "sim_lager_ale_tlv": [
        {"author": "Tal Cohen", "rating": 5, "text": "Best craft beer selection in Tel Aviv. The IPA on tap is phenomenal. Staff really knows their stuff."},
        {"author": "Mia Shapiro", "rating": 5, "text": "Came here for a birthday — the atmosphere was electric. Great cocktails too, not just beer."},
        {"author": "Oren Levi", "rating": 4, "text": "Solid bar. Gets crowded on weekends but the vibe is worth it. Try the pale ale."},
        {"author": "Noa Ben-David", "rating": 5, "text": "My go-to spot after work. Friendly bartenders and rotating seasonal taps."},
        {"author": "Amit Katz", "rating": 3, "text": "Good beer but pricey for what you get. Service was slow on a busy Friday night."},
        {"author": "Shira Mizrahi", "rating": 5, "text": "Finally a bar that takes craft beer seriously in this city. Knowledgeable staff and great food pairings."},
        {"author": "Yossi Peretz", "rating": 4, "text": "Love the industrial design and the long bar. Always something new on tap."},
        {"author": "Dana Goldstein", "rating": 5, "text": "Took my whole team here — everyone loved it. The sampler board is perfect for groups."},
        {"author": "Ron Azulay", "rating": 4, "text": "Great location on Rothschild. Outdoor seating is nice in the evening."},
        {"author": "Hila Stern", "rating": 2, "text": "Had to wait 20 minutes for a drink. Too loud to have a conversation. Beer was fine though."},
        {"author": "Gal Friedman", "rating": 5, "text": "Best beer bar in the city hands down. The stout they had last week was incredible."},
        {"author": "Tamar Ben-Zvi", "rating": 4, "text": "Nice spot. The cheese platter pairs well with the Belgian wheat. Will return."},
        {"author": "Eyal Saar", "rating": 5, "text": "Excellent rotating tap list. Staff recommended a sour I never would have tried — loved it."},
        {"author": "Lior Cohen", "rating": 3, "text": "Decent bar but nothing special. Prices are above average for the area."},
        {"author": "Avital Ron", "rating": 5, "text": "The weekend live music + craft beer combo is unbeatable. Always packed for good reason."},
        {"author": "Nir Hasson", "rating": 4, "text": "Great happy hour deals on weekdays. The porter is outstanding."},
        {"author": "Maya Bar", "rating": 5, "text": "Friendly staff, amazing selection, perfect ambiance. This is my new favorite bar."},
        {"author": "Itai Levy", "rating": 4, "text": "The flight of four beers is great value. Discovered two new favorites."},
        {"author": "Roni Dayan", "rating": 3, "text": "Food was okay, beer was good. Service could be more attentive during peak hours."},
        {"author": "Sari Eliad", "rating": 5, "text": "Came on a Tuesday — quiet, great service, and the bartender walked us through the whole menu. Loved it."},
    ],
    "sim_beer_garden": [
        {"author": "Benny Ofer", "rating": 4, "text": "Beautiful outdoor garden setting. Best place to drink beer in summer. Selection could be wider."},
        {"author": "Iris Shapira", "rating": 5, "text": "The garden is stunning at night with the fairy lights. Relaxed vibe and cold beers."},
        {"author": "Moti Koren", "rating": 3, "text": "Pretty place but the beer selection is mostly mainstream. Go for the atmosphere, not the taps."},
        {"author": "Yael Blum", "rating": 4, "text": "Great for groups. Big tables and fast service. The wheat beer is refreshing."},
        {"author": "Shaul Weiss", "rating": 5, "text": "The garden is magical on a warm evening. Staff are laid back and friendly."},
        {"author": "Dina Gross", "rating": 2, "text": "Overpriced for what it is. Nice garden but I expected better beer options."},
        {"author": "Avi Tzur", "rating": 4, "text": "Good spot for a first date — beautiful setting. Stick to the draft options."},
        {"author": "Lihi Katz", "rating": 5, "text": "We come here every Sunday. The garden brunch with beer is a Tel Aviv institution."},
        {"author": "Doron Ben-Ami", "rating": 3, "text": "Ambiance is great but service is inconsistent. Sometimes fast, sometimes you wait forever."},
        {"author": "Rachel Samson", "rating": 4, "text": "The lager here is crisp and cold. Perfect for a hot day in the garden."},
        {"author": "Kobi Raz", "rating": 5, "text": "Best outdoor bar in the city. The garden is well maintained and the vibe is perfect."},
        {"author": "Tami Biton", "rating": 4, "text": "Food is better than expected for a bar. The burger with the pale ale is a great combo."},
        {"author": "Eli Zur", "rating": 3, "text": "Packed on weekends, hard to find a spot. Worth coming on a weekday."},
        {"author": "Gali Ohayon", "rating": 5, "text": "Discovered this gem last month. The garden is gorgeous and the beer is cold. What more do you need?"},
        {"author": "Amir Ben-Zion", "rating": 4, "text": "Solid neighborhood bar with a great outdoor area. Regular haunt for us."},
        {"author": "Neta Peled", "rating": 3, "text": "Nice garden, average beer. The draft Goldstar is reliable but nothing exciting."},
        {"author": "Udi Barkan", "rating": 5, "text": "The garden in the evening is just beautiful. Perfect for unwinding after work."},
        {"author": "Sigal Mor", "rating": 4, "text": "Friendly staff and nice atmosphere. The cider is surprisingly good here."},
        {"author": "Tzvi Gold", "rating": 2, "text": "Too noisy for a conversation and the beer was warm on arrival. Not impressed."},
        {"author": "Hadas Katz", "rating": 4, "text": "Great for summer evenings. They really nailed the outdoor bar concept."},
    ],
    "sim_tap_room": [
        {"author": "Ilan Sagi", "rating": 5, "text": "The Tap Room is the real deal for craft beer in Tel Aviv. 24 taps and all rotating. Incredible."},
        {"author": "Orly Cohen", "rating": 4, "text": "Serious craft beer bar. The staff can talk for hours about beer styles. Very knowledgeable."},
        {"author": "Barak Levi", "rating": 5, "text": "If you care about craft beer this is your place. They actually import rare stuff you can't find elsewhere."},
        {"author": "Michal Green", "rating": 3, "text": "Good beer selection but the bar is small and cramped. Hard to get a seat on weekends."},
        {"author": "Omer Shahar", "rating": 5, "text": "The DIPA on last week was a 10/10. Knowledgeable staff and constantly changing menu."},
        {"author": "Tali Rosen", "rating": 4, "text": "Love the chalkboard tap list. Something new every time I come. The sour is amazing this week."},
        {"author": "Noam Peretz", "rating": 5, "text": "Best craft beer spot in the city. Full stop. The barrel aged stout was worth every shekel."},
        {"author": "Anat Sela", "rating": 3, "text": "The beer is excellent but the food menu is very limited. Come for drinks only."},
        {"author": "Rafi Mor", "rating": 4, "text": "Tiny bar but big on quality. Standing room only on Thursdays but worth the squeeze."},
        {"author": "Shani Levy", "rating": 5, "text": "The rotating tap list keeps me coming back. Never the same beer twice and always excellent."},
        {"author": "Dotan Katz", "rating": 4, "text": "For beer geeks this is paradise. Staff recommendations are always on point."},
        {"author": "Yonit Bar", "rating": 2, "text": "Too small, too loud, and too crowded. The beer is great but the experience isn't."},
        {"author": "Pini Dagan", "rating": 5, "text": "Found my new favorite bar. The session IPA on tap right now is outstanding."},
        {"author": "Limor Friedman", "rating": 4, "text": "Great beer education here — the staff will help you find exactly what you're looking for."},
        {"author": "Gad Shaul", "rating": 5, "text": "Serious about craft beer in a way no other bar in Tel Aviv is. Highly recommend."},
        {"author": "Ronit Ben-Haim", "rating": 3, "text": "Good selection but pricey. You're paying for the curation though, so fair enough."},
        {"author": "Yaron Elul", "rating": 4, "text": "The flight of four is a great way to explore. Always discover something new."},
        {"author": "Inbal Ziv", "rating": 5, "text": "This is what a craft beer bar should be. No shortcuts, just great beer and passion."},
        {"author": "Moshe Klein", "rating": 4, "text": "Consistent quality across every visit. The double IPA is exceptional."},
        {"author": "Stav Cohen", "rating": 5, "text": "The Tap Room raised the bar (pun intended) for craft beer in this city. Outstanding."},
    ],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def log(msg: str) -> None:
    print(f"  {msg}", flush=True)


def register_or_login(client: httpx.Client) -> str:
    r = client.post("/api/auth/register", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
    if r.status_code == 201:
        log(f"Created demo user: {DEMO_EMAIL}")
        return r.json()["access_token"]
    if r.status_code in (400, 409, 422):
        r2 = client.post("/api/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
        r2.raise_for_status()
        log(f"Logged in as existing demo user: {DEMO_EMAIL}")
        return r2.json()["access_token"]
    r.raise_for_status()
    raise RuntimeError("Unexpected auth response")


def get_or_create_business(client: httpx.Client, headers: dict, biz: dict) -> str:
    r = client.post(
        "/api/businesses",
        json={"place_id": biz["place_id"], "business_type": biz["business_type"]},
        headers=headers,
    )
    if r.status_code == 201:
        biz_id = r.json()["id"]
        log(f"Created business '{biz['name']}' ->{biz_id}")
        return biz_id
    if r.status_code in (400, 409):
        r2 = client.get("/api/businesses", headers=headers)
        r2.raise_for_status()
        for b in r2.json():
            if b["place_id"] == biz["place_id"]:
                log(f"Business '{biz['name']}' already exists ->{b['id']}")
                return b["id"]
    r.raise_for_status()
    raise RuntimeError(f"Could not create/find business {biz['place_id']}")


def seed_sim_reviews(db_url: str, place_id: str, reviews: list[dict]) -> int:
    """Insert reviews into sim_reviews, skipping duplicates. Returns inserted count."""
    import uuid as _uuid
    from datetime import UTC, datetime, timedelta  # noqa: PLC0415

    import sqlalchemy as sa

    engine = sa.create_engine(db_url)
    inserted = 0
    with engine.begin() as conn:
        for i, rev in enumerate(reviews):
            ext_id = f"sim_{place_id}_{i:03d}"
            published_at = datetime.now(UTC) - timedelta(days=len(reviews) - i)
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
                        "id": str(_uuid.uuid4()),
                        "place_id": place_id,
                        "ext_id": ext_id,
                        "author": rev["author"],
                        "rating": rev["rating"],
                        "text": rev["text"],
                        "pub": published_at,
                    },
                )
                inserted += 1
            except Exception as e:
                print(f"    Warning: {e}", flush=True)
    return inserted


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL environment variable is required", file=sys.stderr)
        sys.exit(1)

    print(f"\nSeeding demo world -> {BASE_URL}", flush=True)

    client = httpx.Client(base_url=BASE_URL, timeout=120)

    # 1. Auth
    print("\n[1/5] Auth", flush=True)
    token = register_or_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create businesses
    print("\n[2/5] Businesses", flush=True)
    biz_ids: dict[str, str] = {}
    for biz in BUSINESSES:
        biz_ids[biz["place_id"]] = get_or_create_business(client, headers, biz)

    # 3. Seed sim_reviews
    print("\n[3/5] Seeding sim_reviews table", flush=True)
    for place_id, reviews in REVIEWS.items():
        n = seed_sim_reviews(db_url, place_id, reviews)
        log(f"{place_id}: {n} reviews inserted (skipped duplicates)")

    # 4. Fetch reviews + analyze all businesses
    print("\n[4/5] Fetch reviews + analyze", flush=True)
    hero_id = biz_ids["sim_lager_ale_tlv"]
    for place_id, biz_id in biz_ids.items():
        r = client.post(f"/api/businesses/{biz_id}/fetch-reviews", headers=headers)
        r.raise_for_status()
        log(f"Fetched reviews for {place_id}")

        r = client.post(f"/api/businesses/{biz_id}/analyze", headers=headers)
        if r.status_code == 200:
            log(f"Analysis complete for {place_id}")
        else:
            log(f"Analysis skipped for {place_id}: {r.status_code} {r.text[:100]}")

    # 5. Link competitors + run comparison
    print("\n[5/5] Competitors + comparison", flush=True)
    for place_id in ["sim_beer_garden", "sim_tap_room"]:
        r = client.post(
            f"/api/businesses/{hero_id}/competitors",
            json={"place_id": place_id, "business_type": "bar"},
            headers=headers,
        )
        if r.status_code in (201, 400, 409):
            log(f"Competitor linked: {place_id}")
        else:
            log(f"Competitor link skipped: {r.status_code} {r.text[:100]}")

    r = client.post(f"/api/businesses/{hero_id}/competitors/comparison", headers=headers)
    if r.status_code == 200:
        log("Comparison complete")
    else:
        log(f"Comparison skipped: {r.status_code} {r.text[:100]}")

    print("\nDemo world seeded.", flush=True)
    print(f"  Login: {DEMO_EMAIL} / {DEMO_PASSWORD}", flush=True)
    print(f"  Hero business: {BASE_URL} ->Lager & Ale TLV", flush=True)


if __name__ == "__main__":
    main()
