"""Seed the database with offline demo businesses and competitor links.

Usage (via Docker):
    make seed-offline

Usage (local):
    cd backend
    python -m scripts.seed_offline

Requires a running PostgreSQL database.
Creates a demo user, businesses from the offline manifest, and competitor links.
Safe to re-run — skips entries that already exist.
"""

import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import Base, SessionLocal, engine
from app.models.business import Business
from app.models.competitor_link import CompetitorLink
from app.models.user import User

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "offline"
DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "demo1234"


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        manifest_path = DATA_DIR / "manifest.json"
        if not manifest_path.exists():
            print(f"ERROR: manifest not found at {manifest_path}")
            return

        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)

        user = db.query(User).filter(User.email == DEMO_EMAIL).first()
        if not user:
            import bcrypt
            pw_hash = bcrypt.hashpw(DEMO_PASSWORD.encode(), bcrypt.gensalt()).decode()
            user = User(id=uuid.uuid4(), email=DEMO_EMAIL, hashed_password=pw_hash)
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"Created demo user: {DEMO_EMAIL} / {DEMO_PASSWORD}")
        else:
            print(f"Demo user already exists: {DEMO_EMAIL}")

        biz_map: dict[str, Business] = {}

        for entry in manifest["businesses"]:
            place_id = entry["place_id"]
            existing = (
                db.query(Business)
                .filter(Business.place_id == place_id, Business.user_id == user.id)
                .first()
            )
            if existing:
                print(f"  [exists] {existing.name} ({place_id})")
                biz_map[place_id] = existing
                continue

            biz = Business(
                id=uuid.uuid4(),
                user_id=user.id,
                place_id=place_id,
                name=entry["name"],
                business_type=entry.get("business_type", "other"),
                address=entry.get("address"),
                google_maps_url=None,
                is_competitor=entry["role"] == "competitor",
            )
            db.add(biz)
            db.commit()
            db.refresh(biz)
            biz_map[place_id] = biz
            role_label = "competitor" if biz.is_competitor else "main"
            print(f"  [created] {biz.name} ({place_id}) [{role_label}]")

        scenarios = manifest.get("scenarios", {})
        for scenario_name, scenario in scenarios.items():
            main_id = scenario["main"]
            main_biz = biz_map.get(main_id)
            if not main_biz:
                print(f"\n  WARN: main business {main_id} not found for scenario '{scenario_name}'")
                continue

            for comp_id in scenario.get("competitors", []):
                comp_biz = biz_map.get(comp_id)
                if not comp_biz:
                    print(f"  WARN: competitor {comp_id} not found for scenario '{scenario_name}'")
                    continue

                existing_link = (
                    db.query(CompetitorLink)
                    .filter(
                        CompetitorLink.target_business_id == main_biz.id,
                        CompetitorLink.competitor_business_id == comp_biz.id,
                    )
                    .first()
                )
                if existing_link:
                    print(f"  [linked] {main_biz.name} -> {comp_biz.name} (already)")
                    continue

                link = CompetitorLink(
                    target_business_id=main_biz.id,
                    competitor_business_id=comp_biz.id,
                )
                db.add(link)
                db.commit()
                print(f"  [linked] {main_biz.name} -> {comp_biz.name}")

        print("\n--- Done ---")
        print(f"  Businesses: {len(biz_map)}")
        print(f"  Scenarios:  {len(scenarios)}")
        print()
        print("Next steps:")
        print("  1. Set REVIEW_PROVIDER=offline in backend/.env")
        print(f"  2. Log in as {DEMO_EMAIL} / {DEMO_PASSWORD}")
        print("  3. Fetch reviews + run analysis for each business")
        print("  4. Generate comparisons")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
