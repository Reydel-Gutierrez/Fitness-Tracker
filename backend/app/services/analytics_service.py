from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.analytics.calculations import epley_1rm, set_volume
from app.lib.time import week_start
from app.lib.units import kg_to_display
from app.models.body import BodyMeasurement
from app.models.exercise import Exercise
from app.models.goal import Goal
from app.models.nutrition import NutritionEntry, NutritionTarget
from app.models.session import PerformedExercise, PerformedSet, WorkoutSession
from app.models.user import User
from app.services.body_service import body_stats
from app.services.nutrition_service import day_nutrition
from app.services.program_service import active_program
from app.services.session_service import active_session, calendar_items, list_sessions
from app.services.units_service import get_or_create_profile
from app.services.workout_service import _load_template


def _cutoff(range_key: str) -> date | None:
    today = date.today()
    mapping = {
        "7d": 6,
        "30d": 29,
        "3m": 89,
        "6m": 179,
        "1y": 364,
        "all": None,
    }
    days = mapping.get(range_key.lower(), 29)
    if days is None:
        return None
    return today - timedelta(days=days)


def dashboard(db: Session, user: User, range_key: str = "30d") -> dict:
    profile = get_or_create_profile(db, user)
    wu = profile.weight_unit
    today = date.today()
    start_week = week_start(today)
    body = body_stats(db, user)
    nutrition = day_nutrition(db, user, today)
    sessions = db.scalars(
        select(WorkoutSession)
        .options(
            selectinload(WorkoutSession.exercises).selectinload(PerformedExercise.sets),
            selectinload(WorkoutSession.exercises).selectinload(PerformedExercise.cardio),
            selectinload(WorkoutSession.exercises).selectinload(PerformedExercise.exercise),
        )
        .where(WorkoutSession.user_id == user.id)
        .order_by(WorkoutSession.scheduled_date.asc())
    ).all()
    week_sessions = [s for s in sessions if s.scheduled_date >= start_week and s.status == "completed"]
    program = active_program(db, user)
    scheduled = 0
    if program:
        cur = start_week
        while cur <= today:
            scheduled += sum(1 for w in program["workouts"] if w["weekday"] == cur.weekday())
            cur += timedelta(days=1)
    cutoff = _cutoff(range_key)
    filtered = [s for s in sessions if cutoff is None or s.scheduled_date >= cutoff]

    volume_by_week: dict[str, float] = {}
    for s in filtered:
        if s.status != "completed":
            continue
        key = week_start(s.scheduled_date).isoformat()
        vol = 0.0
        for ex in s.exercises:
            for st in ex.sets:
                if st.completed and not st.skipped:
                    w = st.weight_kg if st.weight_kg is not None else st.added_weight_kg
                    vol += set_volume(w, st.reps)
        volume_by_week[key] = volume_by_week.get(key, 0) + vol

    recent = [
        {
            "id": s.id,
            "name": s.name,
            "date": s.scheduled_date.isoformat(),
            "status": s.status,
            "duration_seconds": s.duration_seconds,
        }
        for s in sorted(sessions, key=lambda x: (x.scheduled_date, x.id), reverse=True)[:8]
    ]

    prs: list[dict] = []
    best: dict[int, float] = {}
    for s in sessions:
        if s.status != "completed":
            continue
        for ex in s.exercises:
            for st in ex.sets:
                if not st.completed or not st.weight_kg:
                    continue
                prev = best.get(ex.exercise_id, 0)
                if st.weight_kg > prev:
                    best[ex.exercise_id] = st.weight_kg
                    if cutoff is None or s.scheduled_date >= cutoff:
                        prs.append(
                            {
                                "date": s.scheduled_date.isoformat(),
                                "exercise": ex.exercise.name if ex.exercise else "",
                                "kind": "weight",
                                "value": kg_to_display(st.weight_kg, wu),
                                "reps": st.reps,
                            }
                        )
    prs = list(reversed(prs))[:8]

    cardio = []
    for s in filtered:
        if s.status != "completed":
            continue
        for ex in s.exercises:
            if ex.cardio and (ex.cardio.completed or ex.cardio.duration_seconds):
                cardio.append(
                    {
                        "date": s.scheduled_date.isoformat(),
                        "name": ex.exercise.name if ex.exercise else "Cardio",
                        "duration_seconds": ex.cardio.duration_seconds,
                        "distance_m": ex.cardio.distance_m,
                    }
                )

    goals = db.scalars(select(Goal).where(Goal.user_id == user.id, Goal.status == "active")).all()
    measurements = db.scalars(
        select(BodyMeasurement)
        .where(BodyMeasurement.user_id == user.id)
        .order_by(BodyMeasurement.measured_on.desc())
        .limit(1)
    ).first()

    today_template = None
    if program:
        for w in program["workouts"]:
            if w["weekday"] == today.weekday():
                today_template = w
                break

    return {
        "cards": {
            "body_weight": body["current"]["weight"] if body.get("current") else None,
            "weight_unit": wu,
            "workouts_this_week": len(week_sessions),
            "scheduled_this_week": scheduled,
            "calories_today": nutrition["totals"]["calories"],
            "calories_target": nutrition["target"]["calories"],
            "protein_today": nutrition["totals"]["protein_g"],
            "protein_target": nutrition["target"]["protein_g"],
        },
        "weight_trend": body["series"],
        "avg_7d": body["avg_7d"],
        "trend_30d": body["trend_30d"],
        "volume_by_week": [
            {"week": k, "volume": kg_to_display(v, wu) or 0} for k, v in sorted(volume_by_week.items())
        ],
        "adherence": {
            "completed": len(week_sessions),
            "scheduled": scheduled,
            "pct": (len(week_sessions) / scheduled * 100) if scheduled else None,
        },
        "recent_workouts": recent,
        "recent_prs": prs,
        "cardio": cardio,
        "goals": [
            {
                "id": g.id,
                "name": g.name,
                "current_value": g.current_value,
                "target_value": g.target_value,
                "unit": g.unit,
                "type": g.type,
            }
            for g in goals
        ],
        "latest_measurement": {
            "date": measurements.measured_on.isoformat(),
            "weight": kg_to_display(measurements.weight_kg, wu) if measurements else None,
        }
        if measurements
        else None,
        "nutrition_today": nutrition,
        "today_workout": today_template,
        "active_session": active_session(db, user),
        "range": range_key,
    }


def today_view(db: Session, user: User) -> dict:
    profile = get_or_create_profile(db, user)
    today = date.today()
    program = active_program(db, user)
    nutrition = day_nutrition(db, user, today)
    body = body_stats(db, user)
    goals = db.scalars(select(Goal).where(Goal.user_id == user.id, Goal.status == "active")).all()
    existing = db.scalars(
        select(WorkoutSession).where(
            WorkoutSession.user_id == user.id,
            WorkoutSession.scheduled_date == today,
        )
    ).all()
    planned = None
    if program:
        for w in program["workouts"]:
            if w["weekday"] == today.weekday():
                planned = w
                break
    is_rest = planned is None
    return {
        "date": today.isoformat(),
        "is_rest_day": is_rest,
        "planned_workout": planned,
        "existing_sessions": [
            {"id": s.id, "name": s.name, "status": s.status, "source": s.source} for s in existing
        ],
        "active_session": active_session(db, user),
        "nutrition": nutrition,
        "body": body["current"],
        "avg_7d": body["avg_7d"],
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
        "checkin_weekday": profile.checkin_weekday,
        "is_checkin_day": today.weekday() == profile.checkin_weekday,
        "weight_unit": profile.weight_unit,
    }


def progress_view(db: Session, user: User, range_key: str = "30d") -> dict:
    profile = get_or_create_profile(db, user)
    wu = profile.weight_unit
    lu = profile.length_unit
    cutoff = _cutoff(range_key)
    body = body_stats(db, user)
    sessions = db.scalars(
        select(WorkoutSession)
        .options(
            selectinload(WorkoutSession.exercises).selectinload(PerformedExercise.sets),
            selectinload(WorkoutSession.exercises).selectinload(PerformedExercise.cardio),
            selectinload(WorkoutSession.exercises).selectinload(PerformedExercise.exercise),
        )
        .where(WorkoutSession.user_id == user.id, WorkoutSession.status == "completed")
        .order_by(WorkoutSession.scheduled_date.asc())
    ).all()
    if cutoff:
        sessions = [s for s in sessions if s.scheduled_date >= cutoff]

    volume_series = []
    freq = {}
    duration_series = []
    muscle_sets: dict[str, int] = {}
    cardio_week: dict[str, dict] = {}
    e1rm: dict[int, list] = {}
    for s in sessions:
        vol = 0.0
        for ex in s.exercises:
            muscles = (ex.exercise.primary_muscles if ex.exercise else None) or []
            for st in ex.sets:
                if st.completed and not st.skipped:
                    w = st.weight_kg if st.weight_kg is not None else st.added_weight_kg
                    vol += set_volume(w, st.reps)
                    for m in muscles:
                        muscle_sets[m] = muscle_sets.get(m, 0) + 1
                    est = epley_1rm(st.weight_kg or 0, st.reps or 0)
                    if est:
                        e1rm.setdefault(ex.exercise_id, []).append(
                            {
                                "date": s.scheduled_date.isoformat(),
                                "name": ex.exercise.name if ex.exercise else "",
                                "e1rm": kg_to_display(est, wu),
                                "weight": kg_to_display(st.weight_kg, wu),
                                "reps": st.reps,
                            }
                        )
            if ex.cardio and (ex.cardio.completed or ex.cardio.duration_seconds):
                key = week_start(s.scheduled_date).isoformat()
                bucket = cardio_week.setdefault(key, {"duration": 0, "distance": 0, "sessions": 0})
                bucket["duration"] += ex.cardio.duration_seconds or 0
                bucket["distance"] += ex.cardio.distance_m or 0
                bucket["sessions"] += 1
        volume_series.append({"date": s.scheduled_date.isoformat(), "volume": kg_to_display(vol, wu) or 0})
        wk = week_start(s.scheduled_date).isoformat()
        freq[wk] = freq.get(wk, 0) + 1
        duration_series.append({"date": s.scheduled_date.isoformat(), "duration_seconds": s.duration_seconds or 0})

    entries = db.scalars(select(NutritionEntry).where(NutritionEntry.user_id == user.id)).all()
    if cutoff:
        entries = [e for e in entries if e.logged_on >= cutoff]
    nutrition_days: dict[str, dict] = {}
    for e in entries:
        key = e.logged_on.isoformat()
        bucket = nutrition_days.setdefault(key, {"calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0})
        bucket["calories"] += e.calories
        bucket["protein_g"] += e.protein_g
        bucket["carbs_g"] += e.carbs_g
        bucket["fat_g"] += e.fat_g

    measurements = db.scalars(
        select(BodyMeasurement)
        .where(BodyMeasurement.user_id == user.id)
        .order_by(BodyMeasurement.measured_on.asc())
    ).all()
    meas_series = []
    from app.lib.units import cm_to_display

    for m in measurements:
        if cutoff and m.measured_on < cutoff:
            continue
        meas_series.append(
            {
                "date": m.measured_on.isoformat(),
                "weight": kg_to_display(m.weight_kg, wu),
                "waist": cm_to_display(m.waist_cm, lu),
                "chest": cm_to_display(m.chest_cm, lu),
                "body_fat_pct": m.body_fat_pct,
            }
        )

    return {
        "range": range_key,
        "weight_unit": wu,
        "length_unit": lu,
        "body": {"weight": body["series"], "measurements": meas_series, "avg_7d": body["avg_7d"], "trend_30d": body["trend_30d"]},
        "training": {
            "volume": volume_series,
            "frequency": [{"week": k, "count": v} for k, v in sorted(freq.items())],
            "duration": duration_series,
            "sets_per_muscle": [{"muscle": k, "sets": v} for k, v in sorted(muscle_sets.items(), key=lambda x: -x[1])],
        },
        "strength": e1rm,
        "cardio": [{"week": k, **v} for k, v in sorted(cardio_week.items())],
        "nutrition": [{"date": k, **v} for k, v in sorted(nutrition_days.items())],
    }


def exercise_history(db: Session, user: User, exercise_id: int) -> dict:
    profile = get_or_create_profile(db, user)
    wu = profile.weight_unit
    rows = db.scalars(
        select(PerformedExercise)
        .options(
            selectinload(PerformedExercise.sets),
            selectinload(PerformedExercise.cardio),
            selectinload(PerformedExercise.session),
        )
        .where(PerformedExercise.exercise_id == exercise_id)
        .order_by(PerformedExercise.id.desc())
    ).all()
    history = []
    pr_weight = None
    pr_1rm = None
    volume_hist = []
    e1rm_hist = []
    for ex in rows:
        sess = ex.session
        if not sess or sess.user_id != user.id or sess.status != "completed":
            continue
        vol = 0.0
        sets = []
        for s in ex.sets:
            if s.completed and not s.skipped:
                w = s.weight_kg if s.weight_kg is not None else s.added_weight_kg
                vol += set_volume(w, s.reps)
                sets.append(
                    {
                        "weight": kg_to_display(s.weight_kg, wu),
                        "reps": s.reps,
                        "rpe": s.rpe,
                    }
                )
                if s.weight_kg and (pr_weight is None or s.weight_kg > pr_weight):
                    pr_weight = s.weight_kg
                est = epley_1rm(s.weight_kg or 0, s.reps or 0)
                if est and (pr_1rm is None or est > pr_1rm):
                    pr_1rm = est
                if est:
                    e1rm_hist.append({"date": sess.scheduled_date.isoformat(), "e1rm": kg_to_display(est, wu)})
        history.append(
            {
                "session_id": sess.id,
                "date": sess.scheduled_date.isoformat(),
                "sets": sets,
                "cardio": {
                    "duration_seconds": ex.cardio.duration_seconds,
                    "distance_m": ex.cardio.distance_m,
                    "rpe": ex.cardio.rpe,
                }
                if ex.cardio
                else None,
            }
        )
        volume_hist.append({"date": sess.scheduled_date.isoformat(), "volume": kg_to_display(vol, wu)})
    return {
        "history": history,
        "volume": list(reversed(volume_hist)),
        "e1rm": list(reversed(e1rm_hist)),
        "prs": {
            "weight": kg_to_display(pr_weight, wu),
            "e1rm": kg_to_display(pr_1rm, wu),
        },
        "weight_unit": wu,
    }
