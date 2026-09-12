from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.lib.security import get_current_user
from app.models.user import User
from app.schemas.session import CardioIn, PerformedSetIn, SessionCreateIn
from app.services.session_service import (
    active_session,
    add_exercise,
    add_set,
    calendar_items,
    finish_session,
    get_session,
    list_sessions,
    remove_set,
    replace_exercise,
    respond_recommendation,
    skip_exercise,
    start_session,
    update_cardio,
    update_exercise_notes,
    update_set,
)

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


class NotesIn(BaseModel):
    notes: str | None = None


class ReplaceIn(BaseModel):
    exercise_id: int


class RecIn(BaseModel):
    status: str


@router.get("")
def list_all(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[dict]:
    return list_sessions(db, user)


@router.get("/active")
def get_active(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict | None:
    return active_session(db, user)


@router.get("/calendar")
def calendar(start: date, end: date, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[dict]:
    return calendar_items(db, user, start, end)


@router.post("")
def start(payload: SessionCreateIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return start_session(db, user, payload)


@router.get("/{session_id}")
def detail(session_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return get_session(db, user, session_id)


@router.post("/{session_id}/finish")
def finish(session_id: int, payload: NotesIn | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return finish_session(db, user, session_id, payload.notes if payload else None)


@router.patch("/{session_id}/sets/{set_id}")
def patch_set(session_id: int, set_id: int, payload: PerformedSetIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return update_set(db, user, session_id, set_id, payload)


@router.post("/{session_id}/exercises/{exercise_id}/sets")
def post_set(session_id: int, exercise_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return add_set(db, user, session_id, exercise_id)


@router.delete("/{session_id}/sets/{set_id}")
def del_set(session_id: int, set_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return remove_set(db, user, session_id, set_id)


@router.patch("/{session_id}/exercises/{exercise_id}/cardio")
def patch_cardio(session_id: int, exercise_id: int, payload: CardioIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return update_cardio(db, user, session_id, exercise_id, payload)


@router.post("/{session_id}/exercises")
def post_ex(session_id: int, payload: ReplaceIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return add_exercise(db, user, session_id, payload.exercise_id)


@router.post("/{session_id}/exercises/{performed_id}/replace")
def replace(session_id: int, performed_id: int, payload: ReplaceIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return replace_exercise(db, user, session_id, performed_id, payload.exercise_id)


@router.post("/{session_id}/exercises/{performed_id}/skip")
def skip(session_id: int, performed_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return skip_exercise(db, user, session_id, performed_id)


@router.patch("/{session_id}/exercises/{performed_id}")
def notes(session_id: int, performed_id: int, payload: NotesIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return update_exercise_notes(db, user, session_id, performed_id, payload.notes)


@router.post("/recommendations/{rec_id}")
def rec(rec_id: int, payload: RecIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return respond_recommendation(db, user, rec_id, payload.status)
