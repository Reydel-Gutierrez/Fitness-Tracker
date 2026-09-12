from datetime import date, timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.calculations import change, moving_average, pct_change
from app.lib.time import utcnow
from app.models.body import BodyMeasurement
from app.models.user import User
from app.schemas.body import MeasurementIn
from app.services.units_service import apply_measurement_input, get_or_create_profile, measurement_to_dict


DISPLAY_KEYS = [
    "weight",
    "body_fat_pct",
    "waist",
    "chest",
    "neck",
    "left_arm",
    "right_arm",
    "hips",
    "left_thigh",
    "right_thigh",
    "left_calf",
    "right_calf",
]


def _diff(current: dict, other: dict | None) -> dict[str, float | None]:
    if not other:
        return {k: None for k in DISPLAY_KEYS}
    return {k: change(current.get(k), other.get(k)) for k in DISPLAY_KEYS}


def serialize_measurement(
    row: BodyMeasurement,
    profile,
    previous: BodyMeasurement | None = None,
    first: BodyMeasurement | None = None,
) -> dict:
    data = measurement_to_dict(row, profile)
    prev = measurement_to_dict(previous, profile) if previous else None
    start = measurement_to_dict(first, profile) if first else None
    data["previous"] = {k: (prev or {}).get(k) for k in DISPLAY_KEYS} if prev else None
    data["change"] = _diff(data, prev)
    data["change_from_start"] = _diff(data, start)
    data["pct_change"] = {k: pct_change(data.get(k), (prev or {}).get(k)) for k in DISPLAY_KEYS} if prev else None
    return data


def list_measurements(db: Session, user: User) -> list[dict]:
    profile = get_or_create_profile(db, user)
    rows = db.scalars(
        select(BodyMeasurement)
        .where(BodyMeasurement.user_id == user.id)
        .order_by(BodyMeasurement.measured_on.asc(), BodyMeasurement.id.asc())
    ).all()
    first = rows[0] if rows else None
    out = []
    for i, row in enumerate(rows):
        prev = rows[i - 1] if i else None
        out.append(serialize_measurement(row, profile, prev, first))
    return list(reversed(out))


def create_measurement(db: Session, user: User, payload: MeasurementIn, source: str = "manual") -> dict:
    profile = get_or_create_profile(db, user)
    row = BodyMeasurement(user_id=user.id)
    apply_measurement_input(row, payload, profile, source=source)
    db.add(row)
    db.commit()
    db.refresh(row)
    rows = db.scalars(
        select(BodyMeasurement)
        .where(BodyMeasurement.user_id == user.id)
        .order_by(BodyMeasurement.measured_on.asc(), BodyMeasurement.id.asc())
    ).all()
    prev = rows[-2] if len(rows) > 1 else None
    first = rows[0]
    return serialize_measurement(row, profile, prev, first)


def delete_measurement(db: Session, user: User, measurement_id: int) -> None:
    row = db.get(BodyMeasurement, measurement_id)
    if not row or row.user_id != user.id:
        raise HTTPException(404, "Measurement not found")
    db.delete(row)
    db.commit()


def body_stats(db: Session, user: User) -> dict:
    profile = get_or_create_profile(db, user)
    rows = db.scalars(
        select(BodyMeasurement)
        .where(BodyMeasurement.user_id == user.id, BodyMeasurement.weight_kg.is_not(None))
        .order_by(BodyMeasurement.measured_on.asc(), BodyMeasurement.id.asc())
    ).all()
    if not rows:
        return {
            "current": None,
            "avg_7d": None,
            "trend_30d": None,
            "series": [],
        }
    latest = serialize_measurement(rows[-1], profile, rows[-2] if len(rows) > 1 else None, rows[0])
    weights = [(r.measured_on, r.weight_kg) for r in rows if r.weight_kg is not None]
    today = date.today()
    last7 = [w for d, w in weights if d >= today - timedelta(days=6)]
    last30 = [w for d, w in weights if d >= today - timedelta(days=29)]
    avg7 = moving_average(last7, 7)
    trend30 = None
    if len(last30) >= 2:
        trend30 = last30[-1] - last30[0]
    wu = profile.weight_unit
    from app.lib.units import kg_to_display

    series = [
        {"date": d.isoformat(), "weight": kg_to_display(w, wu)}
        for d, w in weights
    ]
    return {
        "current": latest,
        "avg_7d": kg_to_display(avg7, wu) if avg7 is not None else None,
        "trend_30d": kg_to_display(trend30, wu) if trend30 is not None else None,
        "series": series,
        "weight_unit": wu,
        "length_unit": profile.length_unit,
    }
