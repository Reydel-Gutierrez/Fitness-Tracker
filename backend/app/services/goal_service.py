from datetime import date

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.goal import Goal
from app.models.user import User
from app.schemas.body import GoalIn


def _progress(goal: Goal) -> float | None:
    if goal.start_value is None or goal.target_value is None or goal.current_value is None:
        return None
    span = goal.target_value - goal.start_value
    if span == 0:
        return 100.0 if goal.current_value == goal.target_value else 0.0
    pct = ((goal.current_value - goal.start_value) / span) * 100
    return max(0.0, min(100.0, pct))


def serialize_goal(goal: Goal) -> dict:
    return {
        "id": goal.id,
        "type": goal.type,
        "name": goal.name,
        "start_value": goal.start_value,
        "current_value": goal.current_value,
        "target_value": goal.target_value,
        "unit": goal.unit,
        "start_date": goal.start_date,
        "target_date": goal.target_date,
        "status": goal.status,
        "measurement_field": goal.measurement_field,
        "exercise_id": goal.exercise_id,
        "notes": goal.notes,
        "progress_pct": _progress(goal),
    }


def list_goals(db: Session, user: User) -> list[dict]:
    rows = db.scalars(select(Goal).where(Goal.user_id == user.id).order_by(Goal.created_at.desc())).all()
    return [serialize_goal(g) for g in rows]


def create_goal(db: Session, user: User, payload: GoalIn) -> dict:
    goal = Goal(
        user_id=user.id,
        type=payload.type,
        name=payload.name,
        start_value=payload.start_value,
        current_value=payload.current_value if payload.current_value is not None else payload.start_value,
        target_value=payload.target_value,
        unit=payload.unit,
        start_date=payload.start_date or date.today(),
        target_date=payload.target_date,
        status=payload.status or "active",
        measurement_field=payload.measurement_field,
        exercise_id=payload.exercise_id,
        notes=payload.notes,
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return serialize_goal(goal)


def update_goal(db: Session, user: User, goal_id: int, payload: GoalIn) -> dict:
    goal = db.get(Goal, goal_id)
    if not goal or goal.user_id != user.id:
        raise HTTPException(404, "Goal not found")
    for field in (
        "type",
        "name",
        "start_value",
        "current_value",
        "target_value",
        "unit",
        "start_date",
        "target_date",
        "status",
        "measurement_field",
        "exercise_id",
        "notes",
    ):
        value = getattr(payload, field)
        if value is not None or field in {"notes", "target_date", "measurement_field", "exercise_id"}:
            if field == "start_date" and value is None:
                continue
            setattr(goal, field, value)
    db.commit()
    db.refresh(goal)
    return serialize_goal(goal)


def delete_goal(db: Session, user: User, goal_id: int) -> None:
    goal = db.get(Goal, goal_id)
    if not goal or goal.user_id != user.id:
        raise HTTPException(404, "Goal not found")
    db.delete(goal)
    db.commit()
