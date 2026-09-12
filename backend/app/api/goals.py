from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.lib.security import get_current_user
from app.models.user import User
from app.schemas.body import GoalIn
from app.services.goal_service import create_goal, delete_goal, list_goals, update_goal

router = APIRouter(prefix="/api/goals", tags=["goals"])


@router.get("")
def get_goals(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[dict]:
    return list_goals(db, user)


@router.post("")
def add_goal(payload: GoalIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return create_goal(db, user, payload)


@router.put("/{goal_id}")
def put_goal(goal_id: int, payload: GoalIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return update_goal(db, user, goal_id, payload)


@router.delete("/{goal_id}")
def remove_goal(goal_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    delete_goal(db, user, goal_id)
    return {"ok": True}
