from datetime import date

from sqlalchemy.orm import Session

from app.lib.units import cm_to_display, display_to_cm, display_to_kg, kg_to_display
from app.models.user import User
from app.schemas.auth import ProfileIn
from app.services.units_service import get_or_create_profile, profile_units


def serialize_profile(user: User) -> dict:
    profile = user.profile
    wu, lu = profile_units(profile)
    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "name": user.name,
            "created_at": user.created_at,
        },
        "date_of_birth": profile.date_of_birth if profile else None,
        "sex": profile.sex if profile else None,
        "height": cm_to_display(profile.height_cm, lu) if profile else None,
        "primary_goal": profile.primary_goal if profile else None,
        "target_weight": kg_to_display(profile.target_weight_kg, wu) if profile else None,
        "experience": profile.experience if profile else None,
        "days_per_week": profile.days_per_week if profile else None,
        "preferred_days": (profile.preferred_days if profile else None) or [],
        "typical_duration_minutes": profile.typical_duration_minutes if profile else None,
        "available_locations": (profile.available_locations if profile else None) or [],
        "available_equipment": (profile.available_equipment if profile else None) or [],
        "limitations": profile.limitations if profile else None,
        "weight_unit": wu,
        "length_unit": lu,
        "checkin_weekday": profile.checkin_weekday if profile else 4,
        "onboarding_completed": profile.onboarding_completed if profile else False,
        "timezone": profile.timezone if profile else None,
    }


def update_profile(db: Session, user: User, payload: ProfileIn) -> dict:
    profile = get_or_create_profile(db, user)
    if payload.name:
        user.name = payload.name
    if payload.weight_unit:
        profile.weight_unit = payload.weight_unit
    if payload.length_unit:
        profile.length_unit = payload.length_unit
    wu, lu = profile.weight_unit, profile.length_unit
    if payload.date_of_birth is not None:
        profile.date_of_birth = payload.date_of_birth
    if payload.sex is not None:
        profile.sex = payload.sex
    if payload.height is not None:
        profile.height_cm = display_to_cm(payload.height, lu)
    if payload.primary_goal is not None:
        profile.primary_goal = payload.primary_goal
    if payload.target_weight is not None:
        profile.target_weight_kg = display_to_kg(payload.target_weight, wu)
    if payload.experience is not None:
        profile.experience = payload.experience
    if payload.days_per_week is not None:
        profile.days_per_week = payload.days_per_week
    if payload.preferred_days is not None:
        profile.preferred_days = payload.preferred_days
    if payload.typical_duration_minutes is not None:
        profile.typical_duration_minutes = payload.typical_duration_minutes
    if payload.available_locations is not None:
        profile.available_locations = payload.available_locations
    if payload.available_equipment is not None:
        profile.available_equipment = payload.available_equipment
    if payload.limitations is not None:
        profile.limitations = payload.limitations
    if payload.checkin_weekday is not None:
        profile.checkin_weekday = payload.checkin_weekday
    if payload.onboarding_completed is not None:
        profile.onboarding_completed = payload.onboarding_completed
    if payload.timezone is not None:
        profile.timezone = payload.timezone
    db.commit()
    db.refresh(user)
    db.refresh(profile)
    return serialize_profile(user)
