from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.lib.security import get_current_user
from app.models.user import User
from app.schemas.nutrition import CheckInIn
from app.services.report_service import create_checkin, get_report, list_checkins

router = APIRouter(prefix="/api/checkins", tags=["checkins"])


@router.get("")
def list_all(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[dict]:
    return list_checkins(db, user)


@router.post("")
def add(payload: CheckInIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return create_checkin(db, user, payload)


reports_router = APIRouter(prefix="/api/reports", tags=["reports"])


@reports_router.get("/weekly")
def weekly(week: date | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return get_report(db, user, week, refresh=True)
