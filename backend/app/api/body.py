from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.lib.security import get_current_user
from app.models.user import User
from app.schemas.body import MeasurementIn
from app.services.body_service import body_stats, create_measurement, delete_measurement, list_measurements

router = APIRouter(prefix="/api/body", tags=["body"])


@router.get("")
def list_body(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[dict]:
    return list_measurements(db, user)


@router.post("")
def add_body(payload: MeasurementIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return create_measurement(db, user, payload)


@router.delete("/{measurement_id}")
def remove_body(measurement_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    delete_measurement(db, user, measurement_id)
    return {"ok": True}


@router.get("/stats")
def stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return body_stats(db, user)
