from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.lib.security import get_current_user
from app.models.user import User
from app.schemas.training import WorkoutTemplateIn
from app.services.workout_service import (
    create_template,
    delete_template,
    duplicate_template,
    get_template,
    list_templates,
    update_template,
)

router = APIRouter(prefix="/api/workouts", tags=["workouts"])


@router.get("")
def list_workouts(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[dict]:
    return list_templates(db, user)


@router.post("")
def add_workout(payload: WorkoutTemplateIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return create_template(db, user, payload)


@router.get("/{template_id}")
def get_workout(template_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return get_template(db, user, template_id)


@router.put("/{template_id}")
def put_workout(template_id: int, payload: WorkoutTemplateIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return update_template(db, user, template_id, payload)


@router.delete("/{template_id}")
def remove_workout(template_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    delete_template(db, user, template_id)
    return {"ok": True}


@router.post("/{template_id}/duplicate")
def dup_workout(template_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return duplicate_template(db, user, template_id)
