from sqlalchemy.orm import Session

from app.models.exercise import Exercise
from app.models.enums import ExerciseType
from app.services.exercise_images import resolve_image_urls


CARDIO_CATEGORIES = {"cardio"}
BODYWEIGHT_EQUIPMENT = {"body only", None, "none", ""}
DISTANCE_NAMES = {"running", "trail", "walk", "jog"}


def infer_exercise_type(item: dict) -> str:
    category = (item.get("category") or "").lower()
    name = (item.get("name") or "").lower()
    equipment = (item.get("equipment") or "") or ""
    equipment = equipment.lower() if isinstance(equipment, str) else ""
    if category in CARDIO_CATEGORIES:
        if any(token in name for token in DISTANCE_NAMES):
            return ExerciseType.DISTANCE
        return ExerciseType.CARDIO
    if category == "stretching":
        return ExerciseType.TIMED
    if equipment in BODYWEIGHT_EQUIPMENT or equipment == "body only":
        return ExerciseType.BODYWEIGHT
    return ExerciseType.STRENGTH


def _instruction_list(instructions) -> list:
    if isinstance(instructions, list):
        return instructions
    return [instructions] if instructions else []


def serialize_exercise(row: Exercise, *, compact: bool = False) -> dict:
    stored_images = row.images or []
    images = resolve_image_urls(stored_images, thumb=False)
    thumbs = resolve_image_urls(stored_images, thumb=True)
    thumbnail = thumbs[0] if thumbs else (images[0] if images else None)
    payload = {
        "id": row.id,
        "name": row.name,
        "source": row.source,
        "exercise_type": row.exercise_type,
        "instructions": [] if compact else _instruction_list(row.instructions),
        "primary_muscles": row.primary_muscles or [],
        "secondary_muscles": row.secondary_muscles or [],
        "equipment": row.equipment or [],
        "difficulty": row.difficulty,
        "category": row.category,
        "images": [] if compact else images,
        "thumbnail": thumbnail,
        "notes": row.notes,
        "is_custom": row.source == "custom",
        "user_id": row.user_id,
    }
    return payload


def seed_images_from_item(item: dict) -> list[str]:
    """Keep the dataset-relative paths (e.g. Barbell_Squat/0.jpg), never remote URLs."""
    images = item.get("images") or []
    out: list[str] = []
    for value in images:
        if not isinstance(value, str):
            continue
        cleaned = value.strip().replace("\\", "/")
        if not cleaned or cleaned.startswith("http://") or cleaned.startswith("https://"):
            continue
        out.append(cleaned.lstrip("/"))
    return out


def seed_exercises(db: Session, items: list[dict]) -> int:
    existing_rows = db.query(Exercise).filter(Exercise.source == "seed").all()
    existing = {e.source_id: e for e in existing_rows}
    added = 0
    updated = 0
    for item in items:
        source_id = str(item.get("id") or item.get("name"))
        images = seed_images_from_item(item)
        row = existing.get(source_id)
        if row is not None:
            if row.images != images:
                row.images = images
                updated += 1
            continue
        equipment = item.get("equipment")
        equipment_list = [equipment] if isinstance(equipment, str) and equipment else equipment or []
        row = Exercise(
            user_id=None,
            source="seed",
            source_id=source_id,
            name=item["name"],
            slug=str(source_id),
            exercise_type=infer_exercise_type(item),
            instructions=item.get("instructions") or [],
            primary_muscles=item.get("primaryMuscles") or [],
            secondary_muscles=item.get("secondaryMuscles") or [],
            equipment=equipment_list,
            difficulty=item.get("level"),
            category=item.get("category"),
            images=images,
        )
        db.add(row)
        added += 1
    if added or updated:
        db.commit()
    return added
