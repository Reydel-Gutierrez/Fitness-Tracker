from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.lib.security import create_access_token, get_current_user, hash_password, verify_password
from app.models.nutrition import NutritionTarget
from app.models.profile import UserProfile
from app.models.user import User
from app.schemas.auth import LoginIn, RegisterIn, TokenResponse, UserOut
from app.services.profile_service import serialize_profile

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=dict)
def register(payload: RegisterIn, db: Session = Depends(get_db)) -> dict:
    email = payload.email.lower().strip()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(400, "Email already registered")
    username = email.split("@")[0]
    base = username
    i = 1
    while db.query(User).filter(User.username == username).first():
        username = f"{base}{i}"
        i += 1
    user = User(
        email=email,
        username=username,
        name=payload.name.strip(),
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.flush()
    db.add(UserProfile(user_id=user.id, preferred_days=[], available_locations=[], available_equipment=[]))
    db.add(NutritionTarget(user_id=user.id))
    db.commit()
    db.refresh(user)
    token = create_access_token(user.id)
    return {"access_token": token, "token_type": "bearer", "user": serialize_profile(user)}


@router.post("/login")
def login(payload: LoginIn, db: Session = Depends(get_db)) -> dict:
    user = db.query(User).filter(User.email == payload.email.lower().strip()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    return {"access_token": create_access_token(user.id), "token_type": "bearer", "user": serialize_profile(user)}


@router.post("/token")
def login_form(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.email == form.username.lower().strip()).first()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me")
def me(user: User = Depends(get_current_user)) -> dict:
    return serialize_profile(user)
