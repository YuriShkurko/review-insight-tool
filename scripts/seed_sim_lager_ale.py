#!/usr/bin/env python3
"""Generate 500 synthetic reviews for sim_lager_ale_tlv.

Narrative arc (all dates relative to 2026-05-01 as "today"):
  Phase 1 — Baseline    (2026-02-01 to 2026-03-02):  ~100 reviews, normal positive bar
  Phase 2 — Festival    (2026-03-03 to 2026-03-20):  ~80  reviews, beer festival buzz
  Phase 3 — Bad keg     (2026-03-21 to 2026-04-12):  ~170 reviews, sour/off-beer complaints
  Phase 4 — Recovery    (2026-04-13 to 2026-05-01):  ~150 reviews, improving, issues resolved

Run from repo root:
    python scripts/seed_sim_lager_ale.py
Output: backend/data/offline/sim_lager_ale_reviews.json
"""

from __future__ import annotations

import json
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

SEED = 42
OUTPUT = Path(__file__).resolve().parents[1] / "backend" / "data" / "offline" / "sim_lager_ale_reviews.json"

# ── Authors ──────────────────────────────────────────────────────────────────

AUTHORS = [
    "Noa Levi", "Avi Cohen", "Tamar Ben David", "Yossi Katz", "Shira Mizrahi",
    "Ronen Shapiro", "Maya Peretz", "Eitan Goldberg", "Hila Friedman", "Gal Nachmias",
    "Omer Alon", "Lihi Segal", "Itay Weiss", "Dana Rosenberg", "Barak Ofer",
    "Tali Haim", "Nadav Ben Ami", "Einat Shachar", "Uri Tzur", "Yael Har-Zion",
    "Michael Stern", "Sophie Dubois", "James O'Brien", "Lena Müller", "Alex Petrov",
    "Chloe Dupont", "Tom Eriksson", "Anna Kowalski", "Pablo Ruiz", "Laura Bianchi",
    "Shlomo Avraham", "Rivka Moreno", "Doron Elias", "Anat Shalev", "Guy Dagan",
    "Michal Brandt", "Ran Tal", "Osnat Ben Moshe", "Yaron Oren", "Inbal Navon",
    "Tzvi Koren", "Merav Luzon", "Assaf Blum", "Sapir Kadosh", "Liron Erez",
    "Nir Ronen", "Hadas Gal", "Amit Shimon", "Reut Vered", "Dor Mansour",
    "Rachel Green", "David Park", "Sarah Wilson", "Kevin O'Connor", "Emma Fischer",
    "Noam Lichtenstein", "Iris Ariel", "Saar Ben Zion", "Limor Hadad", "Yaniv Levy",
    "Carmel Cohen", "Natan Schwartz", "Dafna Harel", "Roi Berkowitz", "Zohar Aloni",
]


# ── Review pools by phase ─────────────────────────────────────────────────────

BASELINE_5 = [
    "One of my favourite bars in Tel Aviv. Cold beer, good music, chill vibe. Perfect after a long day at the office.",
    "Great selection of craft beers on tap. Staff is friendly and prices are fair for Rothschild area.",
    "Love the outdoor seating. Came here with friends on a Thursday night, found a table easily and the service was fast.",
    "Solid neighbourhood bar. The IPAs are always fresh and the food is decent too. Will keep coming back.",
    "Always reliable. Beers are cold, the crowd is nice, and the bartenders know their stuff.",
    "Rothschild Blvd classic. If you want a decent pint without paying tourist prices, this is your spot.",
    "Great atmosphere, especially on Friday afternoon. Came for happy hour and stayed for three hours.",
    "Best tap selection in the area. The wheat beer is excellent. Service was attentive without being pushy.",
    "Friendly staff, great beer garden feel. Good for groups, the tables outside are perfect.",
    "Consistent quality every time. I've been coming here for two years and it never disappoints.",
]
BASELINE_4 = [
    "Good bar, nothing fancy but solid. Beer is cold and the place has a nice vibe. Can get crowded on weekends.",
    "Nice spot on Rothschild. A bit loud inside but the outdoor area is relaxing. Prices are reasonable.",
    "Pleasant experience. Service was a bit slow when busy but the bartender apologised and was helpful.",
    "Decent craft selection. I wish they rotated seasonal taps more often but what's there is good quality.",
    "Fine place for a drink after work. Nothing spectacular but dependable. Would go back.",
    "Good atmosphere, beer is fresh. Parking is a nightmare in this area but that's Tel Aviv for you.",
    "Came on a Tuesday, very relaxed. Chatted with the bartender, got a good recommendation. Enjoyed it.",
    "Pretty good. The outdoor seating is the highlight. Food is okay but beer is the main draw.",
]
BASELINE_3 = [
    "Average bar experience. Beer was fine but service felt rushed. Maybe it was a busy night.",
    "Okay place. A bit overpriced for what it is. Beer selection is standard, nothing special.",
    "Not bad, not great. Took a while to get served. The beer was fine once it arrived.",
]

FESTIVAL_5 = [
    "Came for the craft beer festival and wow — the Rothschild strip was amazing! Lager & Ale had a great selection of guest taps, best booth on the block.",
    "Beer festival weekend was incredible! Tried five different guest craft beers here, all excellent. The festival atmosphere on Rothschild was electric.",
    "Festival vibes were unreal. The staff handled the crowd brilliantly, beers were flowing, great job keeping quality up under the pressure.",
    "Best festival experience yet! Lager & Ale's special festival taps were outstanding. The sour ale they featured was phenomenal.",
    "Five stars for the festival event — long queue but worth every minute. Guest IPA from a local microbrewery was the highlight of my weekend.",
    "Rothschild beer festival does not disappoint and Lager & Ale was the highlight. Exceptional guest taps, knowledgeable staff, perfect evening.",
    "Absolutely buzzing atmosphere during the festival. Managed to try all four guest beers, each one interesting and well-kept. Brilliant event.",
]
FESTIVAL_4 = [
    "Great festival setup. A few teething issues with the queue but the beers were worth it. The saison they were pouring was delicious.",
    "Enjoyed the festival weekend a lot. Lager & Ale held up well under the crowd. Some waits but great atmosphere and beer.",
    "Good festival experience. Tried three new guest taps, two were excellent, one a bit flat. Staff were stretched but friendly.",
    "Fun festival energy on Rothschild. The place was packed but well managed. Special festival pricing was fair too.",
    "Beer festival was a highlight of March. Lager & Ale's setup was good — loved the guest stout they were pouring.",
    "Solid festival showing. A bit cramped but the craft selections were interesting. Will be back next year.",
    "Great beers, lots of energy. The festival tap list was ambitious and mostly delivered. Small gripe: slow bar service.",
]

BAD_KEG_1 = [
    "Something is very wrong with the beer here. Ordered a lager and it tasted sour and metallic — definitely off. Had to send it back.",
    "Got sick after drinking here last night. The beer tasted strange and I had stomach issues all next day. Not acceptable.",
    "The IPA I ordered tasted like vinegar. Clearly a bad keg. Bartender shrugged it off which made it worse. Won't be back.",
    "Disgusting experience. The beer was obviously turned — flat, sour aftertaste, wrong colour. Couldn't finish it.",
    "Beer was clearly off. I know what bad craft tastes like and this was it. Manager was dismissive when I complained.",
    "Terrible. Ordered two beers, both tasted wrong. My friend and I both felt unwell the next morning. Something is definitely wrong.",
    "The wheat beer was noticeably sour — not the good kind. I suspect a dirty line or bad keg. Really disappointed.",
    "I've been coming here for a year and something has changed. The beer is off, there's a strange taste. Won't visit until fixed.",
    "Couldn't finish my beer — tasted sour and fizzy in a bad way. Staff dismissed my concern. Awful experience.",
    "The tap beer was rank. I don't know if it's dirty lines or a bad keg but it ruined the evening. Felt sick the next day.",
]
BAD_KEG_2 = [
    "Not what it used to be. The beer quality has dropped significantly. Something tastes off — probably old keg or dirty lines.",
    "Came after the festival and the quality is noticeably worse. The lager had an off aftertaste. Hope they sort this out.",
    "The IPA was flat and tasted stale. Used to love this place but this visit was a disappointment. Fix the kegs please.",
    "Beer tasted wrong tonight. Not obviously terrible but definitely not right. Strange aftertaste I couldn't place.",
    "Disappointed. The craft selection that was great during the festival is now clearly past its best. Quality control issue.",
    "Something is off with the draught here. Not completely undrinkable but not right either. Won't be back soon.",
    "The beer isn't fresh. Tastes like it's been sitting in a bad line. Staff didn't seem to know or care.",
    "Came with two friends, all three of us noticed the off taste. Staff offered to replace but the second round was the same.",
    "Quality has clearly dropped since the festival. The beers taste flat and slightly sour. A shame.",
]
BAD_KEG_3 = [
    "Average visit, beer was okay but not great. Something slightly off but not terrible. Maybe a new keg that wasn't purged properly.",
    "Beer was a bit flat. Not worth the price. Noticed other tables complaining too. Place needs to sort its draught lines.",
    "Not impressed. The beer quality isn't what I remembered. Staff were friendly but the product let them down.",
]

RECOVERY_5 = [
    "Glad I came back! They clearly sorted out the keg issue — beer is back to its brilliant self. Best IPA I've had in weeks.",
    "Huge improvement! Visited after the bad spell and the quality is back to where it was. The new keg is excellent. Well done for fixing it.",
    "Great recovery! Heard about the issues but decided to give them another chance and I'm so glad I did. Beer was perfect.",
    "Back on form! Had heard the quality had dipped but last night everything was excellent. Lager was crisp and cold, just right.",
    "They've sorted it out. The off-beer issue from a few weeks ago is gone. Beer is excellent again. I'll be a regular again.",
    "Visited after a friend said they fixed the problems and it's true. First-class beer, friendly service, back to being one of my favourite spots.",
    "Good to see the quality restored. The wheat beer in particular is back to its best. Credit to the staff for addressing the issue.",
]
RECOVERY_4 = [
    "Came back to try again after the rough patch and happy to report the beer is much better. Still settling back to the usual standard.",
    "Quality is recovering. Not quite back to peak yet but noticeably better than two weeks ago. On the right track.",
    "Good improvement. The beer is much fresher and cleaner now. A couple more visits and I'll feel confident recommending it again.",
    "Better visit than my last one. Seems like they addressed the draught issues. Beer was decent, not perfect but good.",
    "Glad the problems are being fixed. This visit was good — the lager was properly cold and tasted right again.",
    "Recovery is happening. Beer is back to being enjoyable. Will keep coming back to see if the upward trend holds.",
    "Much better than a few weeks ago. The staff mentioned they replaced the problem kegs and cleaned the lines. It shows.",
    "Back to being a decent bar. Not quite the old Lager & Ale yet but getting there. The service is as good as ever.",
]
RECOVERY_3 = [
    "Improved but not fully back to the standard I expect. Beer was okay, a bit inconsistent. Come back in a few weeks.",
    "Better than the disaster a month ago. Still not the quality I remember from before the festival. Cautiously optimistic.",
    "Getting there. The beer is drinkable again. One keg still tasted a bit off so the clean-up isn't 100% complete.",
]


def rand_dt(rng: random.Random, start: datetime, end: datetime) -> datetime:
    delta = int((end - start).total_seconds())
    offset = rng.randint(0, delta)
    return start + timedelta(seconds=offset)


def build_reviews() -> list[dict]:
    rng = random.Random(SEED)
    reviews: list[dict] = []

    base = datetime(2026, 1, 1, tzinfo=UTC)
    p1_start = base + timedelta(days=31)   # 2026-02-01
    p1_end   = base + timedelta(days=61)   # 2026-03-03
    p2_start = base + timedelta(days=61)   # 2026-03-03
    p2_end   = base + timedelta(days=79)   # 2026-03-21
    p3_start = base + timedelta(days=79)   # 2026-03-21
    p3_end   = base + timedelta(days=102)  # 2026-04-13
    p4_start = base + timedelta(days=102)  # 2026-04-13
    p4_end   = base + timedelta(days=120)  # 2026-05-01

    def pick_author() -> str:
        return rng.choice(AUTHORS)

    # ── Phase 1: Baseline (~100 reviews) ─────────────────────────────────────
    for _ in range(55):
        reviews.append({"author": pick_author(), "rating": 5,
                         "text": rng.choice(BASELINE_5),
                         "published_at": rand_dt(rng, p1_start, p1_end).isoformat()})
    for _ in range(33):
        reviews.append({"author": pick_author(), "rating": 4,
                         "text": rng.choice(BASELINE_4),
                         "published_at": rand_dt(rng, p1_start, p1_end).isoformat()})
    for _ in range(12):
        reviews.append({"author": pick_author(), "rating": 3,
                         "text": rng.choice(BASELINE_3),
                         "published_at": rand_dt(rng, p1_start, p1_end).isoformat()})

    # ── Phase 2: Beer Festival (~80 reviews) ─────────────────────────────────
    for _ in range(45):
        reviews.append({"author": pick_author(), "rating": 5,
                         "text": rng.choice(FESTIVAL_5),
                         "published_at": rand_dt(rng, p2_start, p2_end).isoformat()})
    for _ in range(28):
        reviews.append({"author": pick_author(), "rating": 4,
                         "text": rng.choice(FESTIVAL_4),
                         "published_at": rand_dt(rng, p2_start, p2_end).isoformat()})
    for _ in range(7):
        reviews.append({"author": pick_author(), "rating": 3,
                         "text": rng.choice(BASELINE_3),
                         "published_at": rand_dt(rng, p2_start, p2_end).isoformat()})

    # ── Phase 3: Bad keg crisis (~170 reviews) ───────────────────────────────
    for _ in range(80):
        reviews.append({"author": pick_author(), "rating": 1,
                         "text": rng.choice(BAD_KEG_1),
                         "published_at": rand_dt(rng, p3_start, p3_end).isoformat()})
    for _ in range(55):
        reviews.append({"author": pick_author(), "rating": 2,
                         "text": rng.choice(BAD_KEG_2),
                         "published_at": rand_dt(rng, p3_start, p3_end).isoformat()})
    for _ in range(35):
        reviews.append({"author": pick_author(), "rating": 3,
                         "text": rng.choice(BAD_KEG_3),
                         "published_at": rand_dt(rng, p3_start, p3_end).isoformat()})

    # ── Phase 4: Recovery (~150 reviews) ─────────────────────────────────────
    for _ in range(55):
        reviews.append({"author": pick_author(), "rating": 5,
                         "text": rng.choice(RECOVERY_5),
                         "published_at": rand_dt(rng, p4_start, p4_end).isoformat()})
    for _ in range(65):
        reviews.append({"author": pick_author(), "rating": 4,
                         "text": rng.choice(RECOVERY_4),
                         "published_at": rand_dt(rng, p4_start, p4_end).isoformat()})
    for _ in range(30):
        reviews.append({"author": pick_author(), "rating": 3,
                         "text": rng.choice(RECOVERY_3),
                         "published_at": rand_dt(rng, p4_start, p4_end).isoformat()})

    assert len(reviews) == 500, f"Expected 500 reviews, got {len(reviews)}"

    reviews.sort(key=lambda r: r["published_at"])
    return reviews


def main() -> None:
    reviews = build_reviews()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(reviews, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(reviews)} reviews to {OUTPUT}")
    ratings = [r["rating"] for r in reviews]
    avg = sum(ratings) / len(ratings)
    print(f"Rating distribution: {sorted(set(ratings))} | avg {avg:.2f}")
    from collections import Counter
    dist = Counter(ratings)
    for k in sorted(dist):
        print(f"  {k}*: {dist[k]}")


if __name__ == "__main__":
    main()
