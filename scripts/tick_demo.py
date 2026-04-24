"""Living demo world tick worker — P3: Director arcs + narrative events.

Three layers of modulation, composed multiplicatively:

  Layer 1 — Sine wave (P2): daily rhythm per business with phase offsets
  Layer 2 — Weekly schedule: weekend rush, Sunday brunch, midweek happy hour
  Layer 3 — Narrative arc: 14-day story cycle (festival -> quiet -> bad keg -> recovery)

For arc "burst" moments, generates 1-3 LLM reviews via OpenAI if
OPENAI_API_KEY is set; otherwise falls back to the template bank.

Usage:
    DATABASE_URL=... DEMO_API_URL=http://... python scripts/tick_demo.py
    DATABASE_URL=... DEMO_API_URL=http://... python scripts/tick_demo.py --dry-run
    DATABASE_URL=... DEMO_API_URL=http://... python scripts/tick_demo.py --show-arc

Run every 20-30 minutes via GitHub Actions cron.
"""

from __future__ import annotations

import argparse
import math
import os
import random
import sys
import uuid
from datetime import UTC, datetime, timezone

import httpx

BASE_URL = os.environ.get("DEMO_API_URL", "http://localhost:8000")
DEMO_EMAIL = "demo@review-insight.app"
DEMO_PASSWORD = "DemoWorld2026!"

# Fixed epoch so narrative arcs are globally coherent.
# 2026-04-24 00:00 UTC — day 0 of the first arc cycle.
ARC_EPOCH = 1776988800

# ---------------------------------------------------------------------------
# Layer 1 — Sine wave parameters (daily rhythm, phase-spread per business)
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
        "phase": math.pi / 3,
        "rating_mean": 3.9,
        "rating_std": 0.9,
    },
    "sim_tap_room": {
        "baseline": 1.5,
        "amplitude": 1.4,
        "period": 86400,
        "phase": 2 * math.pi / 3,
        "rating_mean": 4.1,
        "rating_std": 0.8,
    },
}

# ---------------------------------------------------------------------------
# Layer 2 — Weekly schedule
# Each entry: (weekday_start, hour_start, weekday_end, hour_end, {place_id: (volume_mult, rating_delta)})
# weekday: 0=Mon ... 6=Sun  (UTC)
# Ranges are inclusive start, exclusive end.
# First matching window wins.
# ---------------------------------------------------------------------------

WEEKLY_SCHEDULE = [
    # Friday 18:00 - Saturday 23:59: weekend rush
    (4, 18, 5, 24, {
        "sim_lager_ale_tlv": (2.8, 0.30),
        "sim_tap_room":      (2.4, 0.25),
        "sim_beer_garden":   (2.0, 0.20),
    }),
    # Sunday 10:00 - 16:00: Beer Garden brunch dominates
    (6, 10, 6, 16, {
        "sim_beer_garden":   (3.2, 0.50),
        "sim_lager_ale_tlv": (1.3, 0.10),
        "sim_tap_room":      (1.2, 0.05),
    }),
    # Thursday 17:00 - 23:00: pre-weekend buildup
    (3, 17, 3, 23, {
        "sim_lager_ale_tlv": (1.8, 0.20),
        "sim_tap_room":      (1.6, 0.15),
        "sim_beer_garden":   (1.3, 0.05),
    }),
    # Wednesday 17:00 - 21:00: midweek happy hour
    (2, 17, 2, 21, {
        "sim_lager_ale_tlv": (1.6, 0.15),
        "sim_tap_room":      (1.5, 0.10),
        "sim_beer_garden":   (1.2, 0.00),
    }),
    # Monday 00:00 - 12:00: quiet post-weekend dip
    (0, 0, 0, 12, {
        "sim_lager_ale_tlv": (0.5, -0.10),
        "sim_beer_garden":   (0.4, -0.10),
        "sim_tap_room":      (0.5, -0.05),
    }),
]

# ---------------------------------------------------------------------------
# Layer 3 — Narrative arc (14-day cycle from ARC_EPOCH)
# offset_start / offset_end in seconds from the 14-day cycle start.
# modifiers: {place_id: (volume_mult, rating_delta)}
# llm_burst: generate 1-3 OpenAI reviews per burst tick (fallback to templates)
# burst_context: sentence fed to LLM describing the event
# ---------------------------------------------------------------------------

ARC_PERIOD = 14 * 86400  # 14 days

NARRATIVE_ARCS = [
    {
        "name": "festival_weekend",
        "label": "Craft beer festival",
        "offset_start": 0,
        "offset_end": int(2.5 * 86400),
        "modifiers": {
            "sim_lager_ale_tlv": (2.8, 0.40),
            "sim_beer_garden":   (2.2, 0.30),
            "sim_tap_room":      (2.5, 0.35),
        },
        "llm_burst": True,
        "burst_context": "a craft beer festival is happening nearby, drawing enthusiasts from all over Tel Aviv",
    },
    {
        "name": "quiet_week",
        "label": "Quiet period",
        "offset_start": int(2.5 * 86400),
        "offset_end": 7 * 86400,
        "modifiers": {},   # no extra modifier — baseline wave only
        "llm_burst": False,
        "burst_context": "",
    },
    {
        "name": "bad_keg",
        "label": "Bad keg incident at The Tap Room",
        "offset_start": 7 * 86400,
        "offset_end": int(9.5 * 86400),
        "modifiers": {
            "sim_tap_room":      (2.5, -1.60),  # surge of angry reviews
            "sim_lager_ale_tlv": (1.4, 0.10),   # competitors benefit slightly
            "sim_beer_garden":   (1.3, 0.10),
        },
        "llm_burst": True,
        "burst_context": "a bad batch ruined several taps, customers are upset about off-flavors and poor quality control",
    },
    {
        "name": "recovery",
        "label": "Recovery + apology reviews at The Tap Room",
        "offset_start": int(9.5 * 86400),
        "offset_end": 12 * 86400,
        "modifiers": {
            "sim_tap_room":      (2.0, 0.60),  # wave of supportive / returning customers
            "sim_lager_ale_tlv": (1.0, 0.00),
            "sim_beer_garden":   (1.0, 0.00),
        },
        "llm_burst": True,
        "burst_context": "the bar apologized for last week's bad batch, replaced all taps, and regulars are returning to show support",
    },
    {
        "name": "pre_cycle_wind_down",
        "label": "Wind-down before next cycle",
        "offset_start": 12 * 86400,
        "offset_end": ARC_PERIOD,
        "modifiers": {},
        "llm_burst": False,
        "burst_context": "",
    },
]

# ---------------------------------------------------------------------------
# Template bank (40+ reviews per business, mixed ratings)
# ---------------------------------------------------------------------------

TEMPLATES: dict[str, list[dict]] = {
    "sim_lager_ale_tlv": [
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
        {"author": "Dana Freed", "rating": 4, "text": "Great spot, gets crowded on weekends but the quality is consistent. Love the rotating taps."},
        {"author": "Itai Gold", "rating": 4, "text": "Solid bar with real personality. The porter is my regular order. Seating gets tight by 9pm."},
        {"author": "Liron Ben-Zvi", "rating": 4, "text": "Industrial design and long bar are a vibe. Service is fast even when full."},
        {"author": "Ofer Mizrahi", "rating": 4, "text": "Good selection, friendly staff. Slightly pricey but you're paying for curation."},
        {"author": "Ayelet Ron", "rating": 4, "text": "Love the concept — always something on tap I haven't tried. Wish they did more food."},
        {"author": "Nadav Shapiro", "rating": 4, "text": "Great discovery. The flight of four is perfect for exploring without committing to a pint."},
        {"author": "Ilan Gross", "rating": 3, "text": "Good beer, slow service on a busy night. Had to flag someone down twice."},
        {"author": "Tali Sela", "rating": 3, "text": "Nice place but quite loud. Hard to hold a conversation at peak hours."},
        {"author": "Benny Har", "rating": 3, "text": "Decent selection, nothing extraordinary. Prices are on the high side for the area."},
        {"author": "Keren Ziv", "rating": 3, "text": "Waited 15 minutes for a drink on a Friday. Beer was worth it but the wait was frustrating."},
        {"author": "Rami Dor", "rating": 2, "text": "Too crowded and too loud. Had to shout to order. Beer was fine but the experience wasn't."},
        {"author": "Sigal Har-Lev", "rating": 2, "text": "Service felt dismissive. My beer arrived warm and it took forever to get someone's attention."},
        {"author": "Mor Tzur", "rating": 1, "text": "Waited 25 minutes, never got served. Left and went somewhere else. Won't be back."},
    ],
    "sim_beer_garden": [
        {"author": "Yuval Paz", "rating": 5, "text": "The garden at sunset is something else. Cold lager, fairy lights, zero stress."},
        {"author": "Shir Blum", "rating": 5, "text": "Best outdoor bar in the city. We come every Sunday — the brunch + beer combo is a ritual now."},
        {"author": "Avi Stern", "rating": 5, "text": "Magical atmosphere on a warm night. Staff are genuinely friendly and the garden is immaculate."},
        {"author": "Hila Ohayon", "rating": 5, "text": "Took my team here for a celebration. Big tables, great service, everyone was happy."},
        {"author": "Kobi Levi", "rating": 5, "text": "The cider is a hidden gem here. Garden is well maintained and vibe is just right."},
        {"author": "Nurit Ben-David", "rating": 5, "text": "Perfect for a first date — beautiful setting, relaxed pace, good drink list."},
        {"author": "Tal Weiss", "rating": 5, "text": "The garden brunch is an institution. Go on a Sunday morning and thank me later."},
        {"author": "Gadi Mor", "rating": 5, "text": "Came on a Tuesday evening — quiet, gorgeous, and the lager was perfectly cold. Love this place."},
        {"author": "Roni Samson", "rating": 4, "text": "Beautiful outdoor setting. Beer selection is mostly mainstream but the atmosphere makes up for it."},
        {"author": "Inbal Cohen", "rating": 4, "text": "Lovely garden bar. The wheat beer is refreshing and the food is better than expected."},
        {"author": "Yossi Katz", "rating": 4, "text": "Great for groups — big tables and the staff handles crowds well. Wish the tap list were wider."},
        {"author": "Limor Raz", "rating": 4, "text": "Solid neighborhood bar elevated by the outdoor area. The burger + pale ale is the combo."},
        {"author": "Erez Bar", "rating": 4, "text": "Regular haunt for us. Not the most adventurous tap list but reliably good."},
        {"author": "Neta Gold", "rating": 4, "text": "The garden in the evening is beautiful. Service is friendly if a little slow."},
        {"author": "Dina Koren", "rating": 3, "text": "Pretty place but the beer selection is limited to mainstream brands. Go for the atmosphere."},
        {"author": "Amos Tzur", "rating": 3, "text": "Service is inconsistent — sometimes fast, sometimes you're waiting forever. Nice garden though."},
        {"author": "Yael Gross", "rating": 3, "text": "Nice on a weekday. Packed and hard to find a seat on weekends."},
        {"author": "Boaz Ofer", "rating": 3, "text": "Overpriced for what it is. You're paying for the garden, not the beer quality."},
        {"author": "Sari Ben-Zion", "rating": 2, "text": "Beer arrived warm twice. Beautiful space but execution needs work."},
        {"author": "Ran Blum", "rating": 2, "text": "Expected more given the reputation. Noisy, cramped on the weekend, and the service was scattered."},
        {"author": "Dori Azulay", "rating": 1, "text": "Waited 30 minutes, wrong order arrived, never got an apology. Beautiful garden but that's it."},
    ],
    "sim_tap_room": [
        {"author": "Amir Sagi", "rating": 5, "text": "24 taps, all rotating, all excellent. This is the only craft beer bar that really gets it in Tel Aviv."},
        {"author": "Shani Cohen", "rating": 5, "text": "The barrel-aged stout they had last week was the best beer I've had in years. Staff know their stuff."},
        {"author": "Rafi Levi", "rating": 5, "text": "If you care about craft beer this is your place. They import rare stuff you genuinely can't find elsewhere."},
        {"author": "Dotan Peretz", "rating": 5, "text": "The chalkboard tap list changes constantly. Something new every visit. The DIPA right now is extraordinary."},
        {"author": "Orli Bar", "rating": 5, "text": "Staff recommended a sour I would never have picked myself — it was outstanding. Real expertise here."},
        {"author": "Pini Ben-Haim", "rating": 5, "text": "For beer geeks this is paradise. Flight of four is the move for first-timers."},
        {"author": "Moshe Shaul", "rating": 5, "text": "Raised the bar for craft beer in this city. The session IPA on tap now is brilliant."},
        {"author": "Stav Rosen", "rating": 5, "text": "No shortcuts, just great beer and passion. This is what a craft beer bar should be."},
        {"author": "Inbal Mor", "rating": 5, "text": "The rotating list keeps me coming back weekly. Never the same beer twice, always excellent."},
        {"author": "Yonit Ziv", "rating": 5, "text": "Consistent quality across every visit. The double IPA is exceptional and the staff are genuine experts."},
        {"author": "Limor Sela", "rating": 4, "text": "Serious craft beer bar. The staff can talk for hours about beer styles. Very knowledgeable."},
        {"author": "Noam Elul", "rating": 4, "text": "Love the chalkboard tap list. Something new every time. The sour this week is amazing."},
        {"author": "Tali Katz", "rating": 4, "text": "Tiny bar but big on quality. Standing room only on Thursdays but worth the squeeze."},
        {"author": "Ronit Shahar", "rating": 4, "text": "Great beer education — staff will help you find exactly what you're looking for."},
        {"author": "Yaron Green", "rating": 4, "text": "The flight of four is a great way to explore. Always discover something new here."},
        {"author": "Gad Cohen", "rating": 4, "text": "Serious about craft in a way most Tel Aviv bars aren't. Pricey but fair for the curation."},
        {"author": "Anat Friedman", "rating": 3, "text": "The beer is excellent but the bar is small and cramped. Hard to get a seat on weekends."},
        {"author": "Barak Levi", "rating": 3, "text": "Good selection but pricey. You're paying for the curation, which is fair, but still."},
        {"author": "Michal Raz", "rating": 3, "text": "The beer is great but the food menu is very limited. Come for drinks only."},
        {"author": "Omer Klein", "rating": 3, "text": "Amazing tap list, claustrophobic space. Hard to relax when you're shoulder to shoulder."},
        {"author": "Yoni Bar", "rating": 2, "text": "Too small, too loud, too crowded. The beer is great but the experience isn't worth it on weekends."},
        {"author": "Dana Dagan", "rating": 2, "text": "Waited 20 minutes to order at the bar. No apology, no acknowledgement. Beer was good but still."},
        {"author": "Ilan Tzur", "rating": 1, "text": "Turned away at the door — 'too full'. Couldn't even see inside. Never tried, never will."},
    ],
}

# Israeli names pool for LLM-generated reviews (author attribution)
AUTHOR_NAMES = [
    "Dani Katz", "Roni Levi", "Noa Cohen", "Avi Ben-David", "Shira Mizrahi",
    "Tal Goldstein", "Omer Saar", "Lihi Peretz", "Yam Shapiro", "Mor Azulay",
    "Gali Ron", "Erez Stern", "Dana Blum", "Itai Gross", "Tamar Ofer",
    "Adi Weiss", "Nimrod Bar", "Sivan Koren", "Doron Levy", "Hila Tzur",
]

# ---------------------------------------------------------------------------
# Director — Layer 2 + 3 computation
# ---------------------------------------------------------------------------

def get_weekly_modifier(place_id: str, now: datetime) -> tuple[float, float]:
    """Returns (volume_mult, rating_delta) from the weekly schedule."""
    wd = now.weekday()   # 0=Mon, 6=Sun
    hr = now.hour
    for (wd_s, hr_s, wd_e, hr_e, mods) in WEEKLY_SCHEDULE:
        in_window = False
        if wd_s == wd_e:
            in_window = wd == wd_s and hr_s <= hr < hr_e
        elif wd_s < wd_e:
            in_window = (wd == wd_s and hr >= hr_s) or (wd_s < wd < wd_e) or (wd == wd_e and hr < hr_e)
        else:  # wraps week boundary
            in_window = (wd == wd_s and hr >= hr_s) or (wd > wd_s) or (wd < wd_e) or (wd == wd_e and hr < hr_e)
        if in_window:
            vm, rd = mods.get(place_id, (1.0, 0.0))
            return vm, rd
    return 1.0, 0.0


def get_arc(now_ts: float) -> dict | None:
    """Returns the currently active narrative arc (or None during quiet phases)."""
    cycle_pos = (now_ts - ARC_EPOCH) % ARC_PERIOD
    for arc in NARRATIVE_ARCS:
        if arc["offset_start"] <= cycle_pos < arc["offset_end"]:
            return arc
    return None


def get_arc_modifier(place_id: str, arc: dict | None) -> tuple[float, float]:
    if arc is None:
        return 1.0, 0.0
    vm, rd = arc["modifiers"].get(place_id, (1.0, 0.0))
    return vm, rd


# ---------------------------------------------------------------------------
# Wave + modulation
# ---------------------------------------------------------------------------

def compute_tick(place_id: str, now_ts: float, now_dt: datetime) -> tuple[int, float, dict | None]:
    """Return (n_reviews, effective_sentiment, active_arc)."""
    p = WAVE_PARAMS[place_id]
    angle = 2 * math.pi * now_ts / p["period"] + p["phase"]
    sine_val = math.sin(angle)

    arc = get_arc(now_ts)
    w_mult, w_delta = get_weekly_modifier(place_id, now_dt)
    a_mult, a_delta = get_arc_modifier(place_id, arc)

    volume = (p["baseline"] + p["amplitude"] * sine_val) * w_mult * a_mult
    effective_rating_delta = sine_val * 0.5 + w_delta + a_delta

    n = max(0, round(volume))
    return n, effective_rating_delta, arc


def pick_rating(place_id: str, rating_delta: float, rng: random.Random) -> int:
    p = WAVE_PARAMS[place_id]
    mean = p["rating_mean"] + rating_delta
    raw = rng.gauss(mean, p["rating_std"])
    return max(1, min(5, round(raw)))


def pick_template(place_id: str, rating: int, rng: random.Random, used: set) -> dict | None:
    pool = TEMPLATES[place_id]
    for target in [rating, rating - 1, rating + 1, rating - 2, rating + 2]:
        candidates = [t for t in pool if t["rating"] == target and t["author"] not in used]
        if candidates:
            return rng.choice(candidates)
    return None


# ---------------------------------------------------------------------------
# LLM burst — generates arc-flavored reviews via OpenAI (optional)
# ---------------------------------------------------------------------------

BUSINESS_NAMES = {
    "sim_lager_ale_tlv": "Lager & Ale TLV",
    "sim_beer_garden":   "The Beer Garden",
    "sim_tap_room":      "The Tap Room",
}


def generate_llm_reviews(place_id: str, arc: dict, n: int, rng: random.Random) -> list[dict]:
    """Generate n LLM reviews for this arc. Returns [] if openai not available."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return []

    try:
        from openai import OpenAI  # noqa: PLC0415
    except ImportError:
        return []

    client = OpenAI(api_key=api_key)
    bar_name = BUSINESS_NAMES[place_id]
    context = arc["burst_context"]
    results = []

    # Determine target rating band from arc modifier
    _, rating_delta = get_arc_modifier(place_id, arc)
    base_mean = WAVE_PARAMS[place_id]["rating_mean"]
    target_rating = max(1, min(5, round(base_mean + rating_delta)))

    for _ in range(n):
        author = rng.choice(AUTHOR_NAMES)
        star = max(1, min(5, target_rating + rng.randint(-1, 1)))
        prompt = (
            f"Write a {star}-star Google Maps review for a Tel Aviv craft beer bar called '{bar_name}'. "
            f"Context: {context}. "
            f"Write in the first person as a customer named {author}. "
            f"Be specific, conversational, authentic. Under 80 words. No hashtags. "
            f"Output only the review text, no quotes or labels."
        )
        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=120,
                temperature=0.85,
            )
            text = resp.choices[0].message.content.strip()
            results.append({"author": author, "rating": star, "text": text, "source": "llm"})
        except Exception as e:
            print(f"    LLM error: {e}", flush=True)

    return results


# ---------------------------------------------------------------------------
# DB + API helpers
# ---------------------------------------------------------------------------

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
    import sqlalchemy as sa  # noqa: PLC0415

    if dry_run:
        for rev in reviews:
            src = rev.get("source", "template")
            print(f"    [dry-run][{src}] {rev['author']} ({rev['rating']}*) - {rev['text'][:60]}...")
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
    parser.add_argument("--show-arc", action="store_true", help="Print current arc state and exit")
    args = parser.parse_args()

    now = datetime.now(UTC)
    now_ts = now.timestamp()
    rng = random.Random(int(now_ts // 300))

    arc = get_arc(now_ts)
    cycle_day = (now_ts - ARC_EPOCH) % ARC_PERIOD / 86400

    if args.show_arc:
        print(f"Current time:   {now.strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"Arc cycle day:  {cycle_day:.2f} / 14.0")
        print(f"Active arc:     {arc['name'] if arc else 'none'} ({arc['label'] if arc else '-'})")
        print(f"Weekday:        {now.strftime('%A')}  hour={now.hour}")
        for pid in WAVE_PARAMS:
            n, delta, _ = compute_tick(pid, now_ts, now)
            wm, wd = get_weekly_modifier(pid, now)
            am, ad = get_arc_modifier(pid, arc)
            print(f"  {pid:<24}  reviews={n}  rating_delta={delta:+.2f}  weekly_mult={wm:.1f}  arc_mult={am:.1f}")
        return

    db_url = os.environ.get("DATABASE_URL")
    if not db_url and not args.dry_run:
        print("ERROR: DATABASE_URL is required (unless --dry-run)", file=sys.stderr)
        sys.exit(1)

    tag = "[dry-run] " if args.dry_run else ""
    arc_label = arc["label"] if arc else "baseline"
    print(f"\n{tag}Demo world tick -> {BASE_URL}  ({now.strftime('%Y-%m-%d %H:%M UTC')})", flush=True)
    print(f"  Arc: {arc_label}  (cycle day {cycle_day:.1f}/14)  weekday: {now.strftime('%A')}", flush=True)

    client = httpx.Client(base_url=BASE_URL, timeout=60)
    token = login(client)
    headers = {"Authorization": f"Bearer {token}"}

    for place_id in WAVE_PARAMS:
        n_reviews, rating_delta, _ = compute_tick(place_id, now_ts, now)
        direction = "up" if rating_delta > 0.3 else ("down" if rating_delta < -0.3 else "neutral")
        print(f"\n  {place_id}  sentiment={direction} ({rating_delta:+.2f})  reviews_this_tick={n_reviews}", flush=True)

        if n_reviews == 0:
            print("  -> quiet tick, skipping", flush=True)
            continue

        batch: list[dict] = []

        # LLM burst for narrative arc events (up to 2 LLM reviews per tick)
        if arc and arc.get("llm_burst") and place_id in arc["modifiers"]:
            llm_count = min(2, n_reviews)
            llm_reviews = generate_llm_reviews(place_id, arc, llm_count, rng)
            batch.extend(llm_reviews)
            if llm_reviews:
                print(f"  -> {len(llm_reviews)} LLM review(s) generated (arc: {arc['name']})", flush=True)

        # Fill remaining slots with templates
        used_authors = {r["author"] for r in batch}
        for _ in range(n_reviews - len(batch)):
            rating = pick_rating(place_id, rating_delta, rng)
            tmpl = pick_template(place_id, rating, rng, used_authors)
            if tmpl is None:
                break
            used_authors.add(tmpl["author"])
            batch.append({**tmpl, "source": "template"})

        if not batch:
            print("  -> no reviews to insert this tick", flush=True)
            continue

        inserted = insert_reviews(db_url or "", place_id, batch, args.dry_run)
        print(f"  -> inserted {inserted} review(s)", flush=True)

        if args.dry_run:
            continue

        biz_id = get_business_id(client, headers, place_id)
        if not biz_id:
            print(f"  -> business not found, skipping fetch/analyze", flush=True)
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
