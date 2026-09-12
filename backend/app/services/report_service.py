from datetime import date, timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.analytics.calculations import epley_1rm, pct_change, set_volume
from app.lib.time import week_end, week_start
from app.lib.units import kg_to_display
from app.models.body import BodyMeasurement
from app.models.checkin import WeeklyCheckIn, WeeklyReport
from app.models.goal import Goal
from app.models.nutrition import NutritionEntry, NutritionTarget
from app.models.session import PerformedExercise, PerformedSet, WorkoutSession
from app.models.user import User
from app.schemas.nutrition import CheckInIn
from app.services.body_service import create_measurement, serialize_measurement
from app.services.units_service import get_or_create_profile, measurement_to_dict


def _range(day: date) -> tuple[date, date]:
    start = week_start(day)
    return start, week_end(day)


def create_checkin(db: Session, user: User, payload: CheckInIn) -> dict:
    profile = get_or_create_profile(db, user)
    checkin_date = payload.checkin_date or date.today()
    start = week_start(checkin_date)
    existing = db.scalars(
        select(WeeklyCheckIn).where(WeeklyCheckIn.user_id == user.id, WeeklyCheckIn.week_start == start)
    ).first()
    measurement = create_measurement(db, user, payload, source="checkin")
    if existing:
        existing.checkin_date = checkin_date
        existing.body_measurement_id = measurement["id"]
        existing.energy = payload.energy
        existing.sleep_quality = payload.sleep_quality
        existing.stress = payload.stress
        existing.training_satisfaction = payload.training_satisfaction
        existing.notes = payload.notes
        db.commit()
        db.refresh(existing)
        row = existing
    else:
        row = WeeklyCheckIn(
            user_id=user.id,
            week_start=start,
            checkin_date=checkin_date,
            body_measurement_id=measurement["id"],
            energy=payload.energy,
            sleep_quality=payload.sleep_quality,
            stress=payload.stress,
            training_satisfaction=payload.training_satisfaction,
            notes=payload.notes,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
    return serialize_checkin(row, measurement)


def serialize_checkin(row: WeeklyCheckIn, measurement: dict | None = None) -> dict:
    return {
        "id": row.id,
        "week_start": row.week_start,
        "checkin_date": row.checkin_date,
        "energy": row.energy,
        "sleep_quality": row.sleep_quality,
        "stress": row.stress,
        "training_satisfaction": row.training_satisfaction,
        "notes": row.notes,
        "measurement": measurement,
    }


def list_checkins(db: Session, user: User) -> list[dict]:
    profile = get_or_create_profile(db, user)
    rows = db.scalars(
        select(WeeklyCheckIn)
        .options(selectinload(WeeklyCheckIn.body_measurement))
        .where(WeeklyCheckIn.user_id == user.id)
        .order_by(WeeklyCheckIn.week_start.desc())
    ).all()
    out = []
    for row in rows:
        meas = measurement_to_dict(row.body_measurement, profile) if row.body_measurement else None
        out.append(serialize_checkin(row, meas))
    return out


def _sessions_in(db: Session, user_id: int, start: date, end: date) -> list[WorkoutSession]:
    return db.scalars(
        select(WorkoutSession)
        .options(
            selectinload(WorkoutSession.exercises).selectinload(PerformedExercise.sets),
            selectinload(WorkoutSession.exercises).selectinload(PerformedExercise.cardio),
            selectinload(WorkoutSession.exercises).selectinload(PerformedExercise.exercise),
        )
        .where(
            WorkoutSession.user_id == user_id,
            WorkoutSession.scheduled_date >= start,
            WorkoutSession.scheduled_date <= end,
        )
    ).all()


def _volume(sessions: list[WorkoutSession]) -> float:
    total = 0.0
    for sess in sessions:
        if sess.status != "completed":
            continue
        for ex in sess.exercises:
            for s in ex.sets:
                if s.completed and not s.skipped:
                    w = s.weight_kg if s.weight_kg is not None else s.added_weight_kg
                    total += set_volume(w, s.reps)
    return total


def _fmt(n: float | None, digits: int = 1) -> str:
    if n is None:
        return "n/a"
    return f"{n:.{digits}f}".rstrip("0").rstrip(".")


def build_weekly_report(db: Session, user: User, day: date | None = None) -> dict:
    profile = get_or_create_profile(db, user)
    day = day or date.today()
    start, end = _range(day)
    prev_start, prev_end = start - timedelta(days=7), end - timedelta(days=7)
    wu = profile.weight_unit or "lb"
    lu = profile.length_unit or "in"

    this_sessions = _sessions_in(db, user.id, start, end)
    last_sessions = _sessions_in(db, user.id, prev_start, prev_end)
    completed = [s for s in this_sessions if s.status == "completed"]
    last_completed = [s for s in last_sessions if s.status == "completed"]

    from app.services.program_service import active_program

    program = active_program(db, user)
    scheduled_count = 0
    if program:
        cur = start
        while cur <= end:
            scheduled_count += sum(1 for w in program["workouts"] if w["weekday"] == cur.weekday())
            cur += timedelta(days=1)
    adherence = (len(completed) / scheduled_count * 100) if scheduled_count else None

    volume = _volume(this_sessions)
    last_volume = _volume(last_sessions)
    vol_change = pct_change(volume, last_volume) if last_volume else None

    sets_done = 0
    rpes: list[float] = []
    duration = 0
    cardio_sessions = 0
    cardio_duration = 0
    cardio_distance = 0.0
    prs: list[str] = []
    strength_rows: list[dict] = []

    for sess in completed:
        duration += sess.duration_seconds or 0
        for ex in sess.exercises:
            if ex.cardio and ex.cardio.completed:
                cardio_sessions += 1
                cardio_duration += ex.cardio.duration_seconds or 0
                cardio_distance += ex.cardio.distance_m or 0
            for s in ex.sets:
                if s.completed and not s.skipped:
                    sets_done += 1
                    if s.rpe is not None:
                        rpes.append(s.rpe)

    # 1RM changes vs last week
    def best_1rm(sessions: list[WorkoutSession], exercise_id: int) -> float | None:
        best = None
        for sess in sessions:
            if sess.status != "completed":
                continue
            for ex in sess.exercises:
                if ex.exercise_id != exercise_id:
                    continue
                for s in ex.sets:
                    if s.completed and s.weight_kg and s.reps:
                        est = epley_1rm(s.weight_kg, s.reps)
                        if est and (best is None or est > best):
                            best = est
        return best

    exercise_ids = {ex.exercise_id for sess in completed for ex in sess.exercises if not ex.skipped}
    for eid in exercise_ids:
        now = best_1rm(this_sessions, eid)
        prev = best_1rm(last_sessions, eid)
        name = None
        for sess in completed:
            for ex in sess.exercises:
                if ex.exercise_id == eid and ex.exercise:
                    name = ex.exercise.name
        if now:
            strength_rows.append(
                {
                    "exercise_id": eid,
                    "name": name,
                    "e1rm": kg_to_display(now, wu),
                    "e1rm_prev": kg_to_display(prev, wu) if prev else None,
                    "change": kg_to_display(now - prev, wu) if prev else None,
                }
            )
            if prev and now > prev:
                prs.append(
                    f"Your estimated {name} 1RM increased from {_fmt(kg_to_display(prev, wu))} {wu} to {_fmt(kg_to_display(now, wu))} {wu}."
                )

    # body
    def latest_measurement(before: date, after: date | None = None) -> BodyMeasurement | None:
        stmt = select(BodyMeasurement).where(BodyMeasurement.user_id == user.id, BodyMeasurement.measured_on <= before)
        if after:
            stmt = stmt.where(BodyMeasurement.measured_on >= after)
        return db.scalars(stmt.order_by(BodyMeasurement.measured_on.desc(), BodyMeasurement.id.desc())).first()

    this_m = latest_measurement(end, start) or latest_measurement(end)
    last_m = latest_measurement(prev_end, prev_start) or (latest_measurement(start - timedelta(days=1)) if this_m else None)

    weight_now = kg_to_display(this_m.weight_kg, wu) if this_m and this_m.weight_kg else None
    weight_prev = kg_to_display(last_m.weight_kg, wu) if last_m and last_m.weight_kg else None
    from app.lib.units import cm_to_display

    waist_now = cm_to_display(this_m.waist_cm, lu) if this_m else None
    waist_prev = cm_to_display(last_m.waist_cm, lu) if last_m else None

    weights_7 = db.scalars(
        select(BodyMeasurement).where(
            BodyMeasurement.user_id == user.id,
            BodyMeasurement.weight_kg.is_not(None),
            BodyMeasurement.measured_on >= end - timedelta(days=6),
            BodyMeasurement.measured_on <= end,
        )
    ).all()
    avg7 = None
    if len(weights_7) >= 3:
        avg7 = kg_to_display(sum(m.weight_kg for m in weights_7) / len(weights_7), wu)

    # nutrition
    target = db.scalars(select(NutritionTarget).where(NutritionTarget.user_id == user.id)).first()
    entries = db.scalars(
        select(NutritionEntry).where(
            NutritionEntry.user_id == user.id,
            NutritionEntry.logged_on >= start,
            NutritionEntry.logged_on <= end,
        )
    ).all()
    by_day: dict[date, list[NutritionEntry]] = {}
    for e in entries:
        by_day.setdefault(e.logged_on, []).append(e)
    days_cal = 0
    days_pro = 0
    cal_vals = []
    pro_vals = []
    for d, items in by_day.items():
        c = sum(i.calories for i in items)
        p = sum(i.protein_g for i in items)
        cal_vals.append(c)
        pro_vals.append(p)
        if target and c >= target.calories:
            days_cal += 1
        if target and p >= target.protein_g:
            days_pro += 1
    avg_cal = sum(cal_vals) / len(cal_vals) if cal_vals else None
    avg_pro = sum(pro_vals) / len(pro_vals) if pro_vals else None

    goals = db.scalars(select(Goal).where(Goal.user_id == user.id, Goal.status == "active")).all()

    sentences: list[str] = []
    if scheduled_count:
        sentences.append(f"You completed {len(completed)} of {scheduled_count} planned workouts this week.")
    elif completed:
        sentences.append(f"You completed {len(completed)} workout{'s' if len(completed) != 1 else ''} this week.")
    else:
        sentences.append("No completed workouts were logged this week.")

    if vol_change is not None:
        direction = "increased" if vol_change >= 0 else "decreased"
        sentences.append(f"Weekly training volume {direction} {_fmt(abs(vol_change))}% compared with last week.")
    else:
        sentences.append("Not enough data yet to calculate this trend.")

    if weight_now is not None and weight_prev is not None:
        delta = weight_now - weight_prev
        direction = "increased" if delta >= 0 else "decreased"
        sentences.append(f"Body weight {direction} {_fmt(abs(delta), 2)} {wu}.")
    elif weight_now is None:
        sentences.append("Not enough data yet to calculate this trend.")

    if waist_now is not None and waist_prev is not None:
        delta = waist_now - waist_prev
        direction = "increased" if delta >= 0 else "decreased"
        sentences.append(f"Waist measurement {direction} {_fmt(abs(delta), 2)} {lu}.")

    if target and by_day:
        sentences.append(f"You reached your protein target on {days_pro} of {len(by_day)} logged days.")
        sentences.append(f"You reached your calorie target on {days_cal} of {len(by_day)} logged days.")
    elif not by_day:
        sentences.append("Not enough data yet to calculate this trend.")

    payload = {
        "week_start": start.isoformat(),
        "week_end": end.isoformat(),
        "sentences": sentences,
        "body": {
            "weight": weight_now,
            "weight_prev": weight_prev,
            "weight_change": (weight_now - weight_prev) if weight_now is not None and weight_prev is not None else None,
            "avg_7d": avg7,
            "waist": waist_now,
            "waist_prev": waist_prev,
            "waist_change": (waist_now - waist_prev) if waist_now is not None and waist_prev is not None else None,
            "unit_weight": wu,
            "unit_length": lu,
        },
        "training": {
            "scheduled": scheduled_count,
            "completed": len(completed),
            "adherence_pct": adherence,
            "duration_seconds": duration,
            "volume": kg_to_display(volume, wu) if volume else 0,
            "volume_prev": kg_to_display(last_volume, wu) if last_volume else 0,
            "volume_change_pct": vol_change,
            "sets": sets_done,
            "avg_rpe": (sum(rpes) / len(rpes)) if rpes else None,
        },
        "strength": strength_rows,
        "prs": prs,
        "cardio": {
            "sessions": cardio_sessions,
            "duration_seconds": cardio_duration,
            "distance_m": cardio_distance,
        },
        "nutrition": {
            "avg_calories": avg_cal,
            "avg_protein": avg_pro,
            "days_calorie_target": days_cal,
            "days_protein_target": days_pro,
            "days_logged": len(by_day),
        },
        "goals": [
            {
                "id": g.id,
                "name": g.name,
                "current_value": g.current_value,
                "target_value": g.target_value,
                "unit": g.unit,
            }
            for g in goals
        ],
    }
    import json

    existing = db.scalars(
        select(WeeklyReport).where(WeeklyReport.user_id == user.id, WeeklyReport.week_start == start)
    ).first()
    blob = json.dumps(payload, default=str)
    if existing:
        existing.payload = blob
        existing.generated_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    else:
        db.add(WeeklyReport(user_id=user.id, week_start=start, payload=blob))
    db.commit()
    return payload


def get_report(db: Session, user: User, week: date | None = None, refresh: bool = True) -> dict:
    if refresh:
        return build_weekly_report(db, user, week)
    start = week_start(week or date.today())
    row = db.scalars(
        select(WeeklyReport).where(WeeklyReport.user_id == user.id, WeeklyReport.week_start == start)
    ).first()
    if not row:
        return build_weekly_report(db, user, week)
    import json

    return json.loads(row.payload)
