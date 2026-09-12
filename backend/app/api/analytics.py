from datetime import date

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.lib.security import get_current_user
from app.models.user import User
from app.services.analytics_service import dashboard, progress_view, today_view
from app.services.export_service import (
    export_json,
    export_measurements_csv,
    export_nutrition_csv,
    export_sessions_csv,
    export_sets_csv,
)
from app.services.session_service import calendar_items

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/dashboard")
def get_dashboard(range: str = "30d", db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return dashboard(db, user, range)


@router.get("/today")
def get_today(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return today_view(db, user)


@router.get("/progress")
def get_progress(range: str = "30d", db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return progress_view(db, user, range)


export_router = APIRouter(prefix="/api/export", tags=["export"])


@export_router.get("/json")
def json_export(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> JSONResponse:
    data = export_json(db, user)
    return JSONResponse(
        content=data,
        headers={"Content-Disposition": "attachment; filename=fitness-export.json"},
    )


@export_router.get("/measurements.csv")
def meas_csv(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Response:
    return Response(content=export_measurements_csv(db, user), media_type="text/csv")


@export_router.get("/sessions.csv")
def sess_csv(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Response:
    return Response(content=export_sessions_csv(db, user), media_type="text/csv")


@export_router.get("/sets.csv")
def sets_csv(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Response:
    return Response(content=export_sets_csv(db, user), media_type="text/csv")


@export_router.get("/nutrition.csv")
def nutr_csv(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Response:
    return Response(content=export_nutrition_csv(db, user), media_type="text/csv")
