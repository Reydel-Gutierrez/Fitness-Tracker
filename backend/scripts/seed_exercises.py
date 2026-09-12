"""Seed built-in exercises from the vendored free-exercise-db JSON."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.database.session import SessionLocal  # noqa: E402
from app.database.base import Base  # noqa: E402
from app.database.session import engine  # noqa: E402
import app.models  # noqa: E402, F401
from app.services.exercise_images import ensure_local_images  # noqa: E402
from app.services.exercise_seed import seed_exercises  # noqa: E402


def main() -> None:
    Base.metadata.create_all(bind=engine)
    path = ROOT / "seed_data" / "exercises.json"
    items = json.loads(path.read_text(encoding="utf-8"))
    db = SessionLocal()
    try:
        added = seed_exercises(db, items)
        print(f"Seeded {added} exercises from free-exercise-db ({len(items)} in file).")
    finally:
        db.close()
    stats = ensure_local_images(allow_download=True)
    print(
        "Exercise images: "
        f"copied={stats['copied']} downloaded={stats['downloaded']} thumbs={stats['thumbs']}"
    )


if __name__ == "__main__":
    main()
