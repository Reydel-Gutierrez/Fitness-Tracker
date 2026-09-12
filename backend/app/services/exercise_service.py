from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.exercise import Exercise
from app.models.session import PerformedExercise, WorkoutSession
from app.models.user import User
from app.schemas.training import ExerciseIn
from app.services.exercise_images import save_custom_image
from app.services.exercise_seed import serialize_exercise

CARDIO_TYPES = {"cardio", "timed", "distance"}


def _visible(user_id: int):
    return or_(Exercise.user_id.is_(None), Exercise.user_id == user_id)


def _matches_type(row: Exercise, exercise_type: str | None) -> bool:
    if not exercise_type:
        return True
    wanted = exercise_type.lower()
    if wanted == "cardio":
        return row.exercise_type in CARDIO_TYPES
    return row.exercise_type == wanted


def list_exercises(
    db: Session,
    user: User,
    q: str | None = None,
    muscle: str | None = None,
    equipment: str | None = None,
    difficulty: str | None = None,
    category: str | None = None,
    exercise_type: str | None = None,
    compact: bool = True,
) -> list[dict]:
    stmt = select(Exercise).where(_visible(user.id), Exercise.is_archived.is_(False))
    rows = db.scalars(stmt.order_by(Exercise.name.asc())).all()
    out = []
    qn = (q or "").lower().strip()
    for row in rows:
        if qn and qn not in row.name.lower() and qn not in " ".join(row.primary_muscles or []).lower():
            continue
        if muscle and muscle.lower() not in [m.lower() for m in (row.primary_muscles or []) + (row.secondary_muscles or [])]:
            continue
        if equipment and equipment.lower() not in [e.lower() for e in (row.equipment or [])]:
            continue
        if difficulty and (row.difficulty or "").lower() != difficulty.lower():
            continue
        if category and (row.category or "").lower() != category.lower():
            continue
        if not _matches_type(row, exercise_type):
            continue
        out.append(serialize_exercise(row, compact=compact))
    return out


def list_recent_exercises(db: Session, user: User, limit: int = 12) -> list[dict]:
    rows = db.execute(
        select(PerformedExercise.exercise_id, WorkoutSession.started_at, PerformedExercise.id)
        .join(WorkoutSession, PerformedExercise.session_id == WorkoutSession.id)
        .where(WorkoutSession.user_id == user.id)
        .order_by(WorkoutSession.started_at.desc(), PerformedExercise.id.desc())
    ).all()
    seen: set[int] = set()
    ordered_ids: list[int] = []
    for exercise_id, _started, _pid in rows:
        if exercise_id in seen:
            continue
        seen.add(exercise_id)
        ordered_ids.append(exercise_id)
        if len(ordered_ids) >= limit:
            break
    if not ordered_ids:
        return []
    exercises = {
        row.id: row
        for row in db.scalars(select(Exercise).where(Exercise.id.in_(ordered_ids), _visible(user.id))).all()
    }
    return [serialize_exercise(exercises[eid], compact=True) for eid in ordered_ids if eid in exercises]


def get_exercise(db: Session, user: User, exercise_id: int) -> Exercise:
    row = db.get(Exercise, exercise_id)
    if not row or (row.user_id not in (None, user.id)):
        raise HTTPException(404, "Exercise not found")
    return row


def create_exercise(db: Session, user: User, payload: ExerciseIn) -> dict:
    instructions = payload.instructions
    if isinstance(instructions, str):
        instructions = [line.strip() for line in instructions.split("\n") if line.strip()]
    row = Exercise(
        user_id=user.id,
        source="custom",
        source_id=f"custom:{user.id}:{payload.name.lower()}",
        name=payload.name.strip(),
        slug=payload.name.strip().lower().replace(" ", "-"),
        exercise_type=payload.exercise_type,
        instructions=instructions or [],
        primary_muscles=payload.primary_muscles,
        secondary_muscles=payload.secondary_muscles,
        equipment=payload.equipment,
        difficulty=payload.difficulty,
        category=payload.category or payload.exercise_type,
        images=payload.images,
        notes=payload.notes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return serialize_exercise(row)


def update_exercise(db: Session, user: User, exercise_id: int, payload: ExerciseIn) -> dict:
    row = get_exercise(db, user, exercise_id)
    if row.source != "custom" or row.user_id != user.id:
        raise HTTPException(400, "Built-in exercises cannot be edited")
    instructions = payload.instructions
    if isinstance(instructions, str):
        instructions = [line.strip() for line in instructions.split("\n") if line.strip()]
    row.name = payload.name.strip()
    row.exercise_type = payload.exercise_type
    row.instructions = instructions or []
    row.primary_muscles = payload.primary_muscles
    row.secondary_muscles = payload.secondary_muscles
    row.equipment = payload.equipment
    row.difficulty = payload.difficulty
    row.category = payload.category or payload.exercise_type
    row.notes = payload.notes
    row.images = payload.images
    db.commit()
    db.refresh(row)
    return serialize_exercise(row)


def set_custom_image(db: Session, user: User, exercise_id: int, data: bytes, filename: str | None = None) -> dict:
    row = get_exercise(db, user, exercise_id)
    if row.source != "custom" or row.user_id != user.id:
        raise HTTPException(400, "Only custom exercises can have an uploaded image")
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(400, "Image must be 5 MB or smaller")
    try:
        rel = save_custom_image(exercise_id, data, filename)
    except Exception as exc:
        raise HTTPException(400, "Could not read that image") from exc
    row.images = [rel]
    db.commit()
    db.refresh(row)
    return serialize_exercise(row)


def archive_exercise(db: Session, user: User, exercise_id: int) -> None:
    row = get_exercise(db, user, exercise_id)
    if row.source != "custom" or row.user_id != user.id:
        raise HTTPException(400, "Built-in exercises cannot be deleted")
    row.is_archived = True
    db.commit()
