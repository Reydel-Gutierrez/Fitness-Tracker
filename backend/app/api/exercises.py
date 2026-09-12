from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.lib.security import get_current_user
from app.models.user import User
from app.schemas.training import ExerciseIn
from app.services.analytics_service import exercise_history
from app.services.exercise_seed import serialize_exercise
from app.services.exercise_service import (
    archive_exercise,
    create_exercise,
    get_exercise,
    list_exercises,
    list_recent_exercises,
    set_custom_image,
    update_exercise,
)

router = APIRouter(prefix="/api/exercises", tags=["exercises"])


@router.get("")
def search(
    q: str | None = None,
    muscle: str | None = None,
    equipment: str | None = None,
    difficulty: str | None = None,
    category: str | None = None,
    exercise_type: str | None = None,
    compact: bool = Query(default=True),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[dict]:
    return list_exercises(db, user, q, muscle, equipment, difficulty, category, exercise_type, compact)


@router.post("")
def add(payload: ExerciseIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return create_exercise(db, user, payload)


@router.get("/recent")
def recent(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[dict]:
    return list_recent_exercises(db, user)


@router.get("/{exercise_id}")
def detail(exercise_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    row = get_exercise(db, user, exercise_id)
    data = serialize_exercise(row)
    data["stats"] = exercise_history(db, user, exercise_id)
    return data


@router.post("/{exercise_id}/image")
async def upload_image(
    exercise_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    data = await file.read()
    return set_custom_image(db, user, exercise_id, data, file.filename)


@router.put("/{exercise_id}")
def edit(exercise_id: int, payload: ExerciseIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return update_exercise(db, user, exercise_id, payload)


@router.delete("/{exercise_id}")
def remove(exercise_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    archive_exercise(db, user, exercise_id)
    return {"ok": True}
