from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.lib.security import get_current_user
from app.models.user import User
from app.schemas.auth import ProfileIn
from app.services.profile_service import serialize_profile, update_profile

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("")
def get_profile(user: User = Depends(get_current_user)) -> dict:
    return serialize_profile(user)


@router.put("")
def put_profile(payload: ProfileIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    return update_profile(db, user, payload)
