"""Optional demo data. Never run automatically in production."""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.database.base import Base  # noqa: E402
from app.database.session import SessionLocal, engine  # noqa: E402
from app.lib.security import hash_password  # noqa: E402
from app.models.body import BodyMeasurement  # noqa: E402
from app.models.nutrition import NutritionEntry, NutritionTarget  # noqa: E402
from app.models.profile import UserProfile  # noqa: E402
from app.models.user import User  # noqa: E402
import app.models  # noqa: E402, F401


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == "demo@local").first():
            print("Demo user already exists (demo@local / demodemo).")
            return
        user = User(
            email="demo@local",
            username="demo",
            name="Demo Athlete",
            password_hash=hash_password("demodemo"),
        )
        db.add(user)
        db.flush()
        db.add(
            UserProfile(
                user_id=user.id,
                height_cm=178,
                primary_goal="build_strength",
                experience="intermediate",
                days_per_week=4,
                preferred_days=[0, 1, 3, 5],
                typical_duration_minutes=60,
                available_locations=["gym", "home"],
                available_equipment=["barbell", "dumbbells", "pull-up bar", "bodyweight"],
                weight_unit="lb",
                length_unit="in",
                onboarding_completed=True,
            )
        )
        db.add(NutritionTarget(user_id=user.id, calories=2400, protein_g=180, carbs_g=250, fat_g=70))
        today = date.today()
        for i, w in enumerate([82.5, 82.3, 82.1, 81.8]):
            db.add(BodyMeasurement(user_id=user.id, measured_on=today - timedelta(days=(3 - i) * 7), weight_kg=w, source="demo"))
        db.add(
            NutritionEntry(
                user_id=user.id,
                logged_on=today,
                meal="breakfast",
                name="Demo oats (not production data)",
                calories=420,
                protein_g=22,
                carbs_g=60,
                fat_g=10,
            )
        )
        db.commit()
        print("Created DEMO user demo@local / demodemo. This data is labeled demo and is optional.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
