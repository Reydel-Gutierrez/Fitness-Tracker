from datetime import date

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.nutrition import Food, NutritionEntry, NutritionTarget
from app.models.user import User
from app.schemas.nutrition import FoodIn, NutritionEntryIn, NutritionTargetIn


def serialize_food(food: Food) -> dict:
    return {
        "id": food.id,
        "name": food.name,
        "serving_description": food.serving_description,
        "calories": food.calories,
        "protein_g": food.protein_g,
        "carbs_g": food.carbs_g,
        "fat_g": food.fat_g,
        "fiber_g": food.fiber_g,
        "use_count": food.use_count,
        "source": food.source,
    }


def get_or_create_target(db: Session, user: User) -> NutritionTarget:
    target = db.scalars(select(NutritionTarget).where(NutritionTarget.user_id == user.id)).first()
    if not target:
        target = NutritionTarget(user_id=user.id)
        db.add(target)
        db.commit()
        db.refresh(target)
    return target


def day_nutrition(db: Session, user: User, day: date) -> dict:
    entries = db.scalars(
        select(NutritionEntry)
        .where(NutritionEntry.user_id == user.id, NutritionEntry.logged_on == day)
        .order_by(NutritionEntry.id.asc())
    ).all()
    target = get_or_create_target(db, user)
    totals = {
        "calories": sum(e.calories for e in entries),
        "protein_g": sum(e.protein_g for e in entries),
        "carbs_g": sum(e.carbs_g for e in entries),
        "fat_g": sum(e.fat_g for e in entries),
        "fiber_g": sum(e.fiber_g or 0 for e in entries),
    }
    tgt = {
        "calories": target.calories,
        "protein_g": target.protein_g,
        "carbs_g": target.carbs_g,
        "fat_g": target.fat_g,
    }
    return {
        "date": day,
        "entries": [
            {
                "id": e.id,
                "logged_on": e.logged_on,
                "meal": e.meal,
                "name": e.name,
                "food_id": e.food_id,
                "quantity": e.quantity,
                "calories": e.calories,
                "protein_g": e.protein_g,
                "carbs_g": e.carbs_g,
                "fat_g": e.fat_g,
                "fiber_g": e.fiber_g,
            }
            for e in entries
        ],
        "totals": totals,
        "target": tgt,
        "consumed_vs_target": {
            key: {"consumed": totals[key], "target": tgt[key]}
            for key in ("calories", "protein_g", "carbs_g", "fat_g")
        },
    }


def list_foods(db: Session, user: User, q: str | None = None) -> list[dict]:
    rows = db.scalars(
        select(Food).where(Food.user_id == user.id).order_by(Food.use_count.desc(), Food.name.asc())
    ).all()
    if q:
        qn = q.lower()
        rows = [r for r in rows if qn in r.name.lower()]
    return [serialize_food(r) for r in rows]


def create_food(db: Session, user: User, payload: FoodIn) -> dict:
    food = Food(user_id=user.id, **payload.model_dump())
    db.add(food)
    db.commit()
    db.refresh(food)
    return serialize_food(food)


def log_entry(db: Session, user: User, payload: NutritionEntryIn) -> dict:
    day = payload.logged_on or date.today()
    name = payload.name
    calories = payload.calories
    protein = payload.protein_g
    carbs = payload.carbs_g
    fat = payload.fat_g
    fiber = payload.fiber_g
    food = None
    if payload.food_id:
        food = db.get(Food, payload.food_id)
        if not food or food.user_id != user.id:
            raise HTTPException(404, "Food not found")
        qty = payload.quantity or 1
        name = food.name
        calories = food.calories * qty
        protein = food.protein_g * qty
        carbs = food.carbs_g * qty
        fat = food.fat_g * qty
        fiber = (food.fiber_g or 0) * qty if food.fiber_g is not None else None
        food.use_count += 1
    elif name and calories is not None:
        existing = db.scalars(
            select(Food).where(Food.user_id == user.id, Food.name == name)
        ).first()
        if not existing:
            food = Food(
                user_id=user.id,
                name=name,
                serving_description=payload.serving_description or "1 serving",
                calories=calories,
                protein_g=protein or 0,
                carbs_g=carbs or 0,
                fat_g=fat or 0,
                fiber_g=fiber,
                use_count=1,
            )
            db.add(food)
        else:
            existing.use_count += 1
    if not name:
        raise HTTPException(400, "Food name is required")
    entry = NutritionEntry(
        user_id=user.id,
        food_id=food.id if food else payload.food_id,
        logged_on=day,
        meal=payload.meal,
        name=name,
        quantity=payload.quantity or 1,
        calories=calories or 0,
        protein_g=protein or 0,
        carbs_g=carbs or 0,
        fat_g=fat or 0,
        fiber_g=fiber,
    )
    db.add(entry)
    db.commit()
    return day_nutrition(db, user, day)


def update_entry(db: Session, user: User, entry_id: int, payload: NutritionEntryIn) -> dict:
    entry = db.get(NutritionEntry, entry_id)
    if not entry or entry.user_id != user.id:
        raise HTTPException(404, "Entry not found")
    if payload.name:
        entry.name = payload.name
    if payload.meal:
        entry.meal = payload.meal
    if payload.quantity is not None:
        entry.quantity = payload.quantity
    if payload.calories is not None:
        entry.calories = payload.calories
    if payload.protein_g is not None:
        entry.protein_g = payload.protein_g
    if payload.carbs_g is not None:
        entry.carbs_g = payload.carbs_g
    if payload.fat_g is not None:
        entry.fat_g = payload.fat_g
    if payload.fiber_g is not None:
        entry.fiber_g = payload.fiber_g
    db.commit()
    return day_nutrition(db, user, entry.logged_on)


def delete_entry(db: Session, user: User, entry_id: int) -> dict:
    entry = db.get(NutritionEntry, entry_id)
    if not entry or entry.user_id != user.id:
        raise HTTPException(404, "Entry not found")
    day = entry.logged_on
    db.delete(entry)
    db.commit()
    return day_nutrition(db, user, day)


def update_target(db: Session, user: User, payload: NutritionTargetIn) -> dict:
    target = get_or_create_target(db, user)
    target.calories = payload.calories
    target.protein_g = payload.protein_g
    target.carbs_g = payload.carbs_g
    target.fat_g = payload.fat_g
    db.commit()
    return {
        "calories": target.calories,
        "protein_g": target.protein_g,
        "carbs_g": target.carbs_g,
        "fat_g": target.fat_g,
    }
