from datetime import date

from sqlalchemy.orm import Session

from app.lib.units import cm_to_display, display_to_cm, display_to_kg, kg_to_display
from app.lib.time import utcnow, week_start
from app.models.body import BodyMeasurement
from app.models.profile import UserProfile
from app.models.user import User


MEASURE_FIELDS = [
    ("weight", "weight_kg", "weight"),
    ("body_fat_pct", "body_fat_pct", "percent"),
    ("waist", "waist_cm", "length"),
    ("chest", "chest_cm", "length"),
    ("neck", "neck_cm", "length"),
    ("left_arm", "left_arm_cm", "length"),
    ("right_arm", "right_arm_cm", "length"),
    ("hips", "hips_cm", "length"),
    ("left_thigh", "left_thigh_cm", "length"),
    ("right_thigh", "right_thigh_cm", "length"),
    ("left_calf", "left_calf_cm", "length"),
    ("right_calf", "right_calf_cm", "length"),
]


def profile_units(profile: UserProfile | None) -> tuple[str, str]:
    if not profile:
        return "lb", "in"
    return profile.weight_unit or "lb", profile.length_unit or "in"


def to_kg(value: float | None, profile: UserProfile | None) -> float | None:
    return display_to_kg(value, profile_units(profile)[0])


def from_kg(value: float | None, profile: UserProfile | None) -> float | None:
    return kg_to_display(value, profile_units(profile)[0])


def to_cm(value: float | None, profile: UserProfile | None) -> float | None:
    return display_to_cm(value, profile_units(profile)[1])


def from_cm(value: float | None, profile: UserProfile | None) -> float | None:
    return cm_to_display(value, profile_units(profile)[1])


def measurement_to_dict(row: BodyMeasurement, profile: UserProfile | None, extras: bool = False) -> dict:
    wu, lu = profile_units(profile)
    data = {
        "id": row.id,
        "measured_on": row.measured_on,
        "weight": kg_to_display(row.weight_kg, wu),
        "body_fat_pct": row.body_fat_pct,
        "waist": cm_to_display(row.waist_cm, lu),
        "chest": cm_to_display(row.chest_cm, lu),
        "neck": cm_to_display(row.neck_cm, lu),
        "left_arm": cm_to_display(row.left_arm_cm, lu),
        "right_arm": cm_to_display(row.right_arm_cm, lu),
        "hips": cm_to_display(row.hips_cm, lu),
        "left_thigh": cm_to_display(row.left_thigh_cm, lu),
        "right_thigh": cm_to_display(row.right_thigh_cm, lu),
        "left_calf": cm_to_display(row.left_calf_cm, lu),
        "right_calf": cm_to_display(row.right_calf_cm, lu),
        "notes": row.notes,
        "source": row.source,
        "created_at": row.created_at,
        "weight_unit": wu,
        "length_unit": lu,
    }
    return data


def apply_measurement_input(row: BodyMeasurement, payload, profile: UserProfile | None, source: str = "manual") -> None:
    row.measured_on = payload.measured_on or date.today()
    row.weight_kg = to_kg(payload.weight, profile)
    row.body_fat_pct = payload.body_fat_pct
    row.waist_cm = to_cm(payload.waist, profile)
    row.chest_cm = to_cm(payload.chest, profile)
    row.neck_cm = to_cm(payload.neck, profile)
    row.left_arm_cm = to_cm(payload.left_arm, profile)
    row.right_arm_cm = to_cm(payload.right_arm, profile)
    row.hips_cm = to_cm(payload.hips, profile)
    row.left_thigh_cm = to_cm(payload.left_thigh, profile)
    row.right_thigh_cm = to_cm(payload.right_thigh, profile)
    row.left_calf_cm = to_cm(payload.left_calf, profile)
    row.right_calf_cm = to_cm(payload.right_calf, profile)
    row.notes = payload.notes
    row.source = source


def get_or_create_profile(db: Session, user: User) -> UserProfile:
    if user.profile:
        return user.profile
    profile = UserProfile(user_id=user.id, preferred_days=[], available_locations=[], available_equipment=[])
    db.add(profile)
    db.flush()
    user.profile = profile
    return profile
