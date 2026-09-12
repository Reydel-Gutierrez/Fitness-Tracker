from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.lib.security import get_current_user
from app.models.user import User
from app.schemas.nutrition import FoodIn, NutritionEntryIn, NutritionTargetIn
from app.services.nutrition_service import (
    create_food,
    day_nutrition,
    delete_entry,
    get_or_create_target,
    list_foods,
    log_entry,
    update_entry,
    update_target,
)

router = APIRouter(prefix="/api/nutrition", tags=["nutrition"])


@router.get("/day")
def get_day(day: date | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return day_nutrition(db, user, day or date.today())


@router.get("/foods")
def foods(q: str | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[dict]:
    return list_foods(db, user, q)


@router.post("/foods")
def add_food(payload: FoodIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return create_food(db, user, payload)


@router.post("/entries")
def add_entry(payload: NutritionEntryIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return log_entry(db, user, payload)


@router.put("/entries/{entry_id}")
def put_entry(entry_id: int, payload: NutritionEntryIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return update_entry(db, user, entry_id, payload)


@router.delete("/entries/{entry_id}")
def del_entry(entry_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return delete_entry(db, user, entry_id)


@router.get("/target")
def get_target(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    t = get_or_create_target(db, user)
    return {"calories": t.calories, "protein_g": t.protein_g, "carbs_g": t.carbs_g, "fat_g": t.fat_g}


@router.put("/target")
def put_target(payload: NutritionTargetIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return update_target(db, user, payload)
