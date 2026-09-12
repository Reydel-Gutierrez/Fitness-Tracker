from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.lib.security import get_current_user
from app.models.user import User
from app.schemas.training import ProgramIn
from app.services.program_service import (
    active_program,
    create_program,
    delete_program,
    generate_and_save,
    get_program,
    list_programs,
    update_program,
)

router = APIRouter(prefix="/api/programs", tags=["programs"])


@router.get("")
def list_all(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[dict]:
    return list_programs(db, user)


@router.get("/active")
def get_active(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict | None:
    return active_program(db, user)


@router.post("")
def add(payload: ProgramIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return create_program(db, user, payload)


@router.post("/generate")
def generate(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return generate_and_save(db, user)


@router.get("/{program_id}")
def detail(program_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return get_program(db, user, program_id)


@router.put("/{program_id}")
def edit(program_id: int, payload: ProgramIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return update_program(db, user, program_id, payload)


@router.delete("/{program_id}")
def remove(program_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    delete_program(db, user, program_id)
    return {"ok": True}
