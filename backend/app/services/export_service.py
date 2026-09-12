import csv
import io
import json
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.body import BodyMeasurement
from app.models.exercise import Exercise
from app.models.goal import Goal
from app.models.nutrition import Food, NutritionEntry, NutritionTarget
from app.models.program import Program
from app.models.session import PerformedExercise, PerformedSet, WorkoutSession
from app.models.user import User
from app.models.workout import WorkoutTemplate
from app.services.units_service import get_or_create_profile, measurement_to_dict
from app.lib.units import kg_to_display


def export_json(db: Session, user: User) -> dict:
    profile = get_or_create_profile(db, user)
    measurements = db.scalars(select(BodyMeasurement).where(BodyMeasurement.user_id == user.id)).all()
    sessions = db.scalars(
        select(WorkoutSession)
        .options(
            selectinload(WorkoutSession.exercises).selectinload(PerformedExercise.sets),
            selectinload(WorkoutSession.exercises).selectinload(PerformedExercise.cardio),
            selectinload(WorkoutSession.exercises).selectinload(PerformedExercise.exercise),
        )
        .where(WorkoutSession.user_id == user.id)
    ).all()
    foods = db.scalars(select(Food).where(Food.user_id == user.id)).all()
    entries = db.scalars(select(NutritionEntry).where(NutritionEntry.user_id == user.id)).all()
    goals = db.scalars(select(Goal).where(Goal.user_id == user.id)).all()
    custom_ex = db.scalars(select(Exercise).where(Exercise.user_id == user.id)).all()
    return {
        "exported_on": date.today().isoformat(),
        "user": {"email": user.email, "name": user.name},
        "profile": {
            "primary_goal": profile.primary_goal,
            "experience": profile.experience,
            "weight_unit": profile.weight_unit,
            "length_unit": profile.length_unit,
        },
        "measurements": [measurement_to_dict(m, profile) for m in measurements],
        "goals": [
            {
                "type": g.type,
                "name": g.name,
                "start_value": g.start_value,
                "current_value": g.current_value,
                "target_value": g.target_value,
                "unit": g.unit,
                "status": g.status,
            }
            for g in goals
        ],
        "custom_exercises": [{"name": e.name, "exercise_type": e.exercise_type} for e in custom_ex],
        "sessions": [
            {
                "name": s.name,
                "date": s.scheduled_date.isoformat(),
                "status": s.status,
                "notes": s.notes,
                "exercises": [
                    {
                        "name": ex.exercise.name if ex.exercise else None,
                        "sets": [
                            {
                                "set_number": st.set_number,
                                "weight": kg_to_display(st.weight_kg, profile.weight_unit),
                                "reps": st.reps,
                                "rpe": st.rpe,
                                "completed": st.completed,
                            }
                            for st in ex.sets
                        ],
                    }
                    for ex in s.exercises
                ],
            }
            for s in sessions
        ],
        "nutrition": [
            {
                "date": e.logged_on.isoformat(),
                "meal": e.meal,
                "name": e.name,
                "calories": e.calories,
                "protein_g": e.protein_g,
                "carbs_g": e.carbs_g,
                "fat_g": e.fat_g,
            }
            for e in entries
        ],
        "foods": [{"name": f.name, "calories": f.calories, "protein_g": f.protein_g} for f in foods],
    }


def csv_text(headers: list[str], rows: list[list]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    writer.writerows(rows)
    return buf.getvalue()


def export_measurements_csv(db: Session, user: User) -> str:
    profile = get_or_create_profile(db, user)
    rows = db.scalars(select(BodyMeasurement).where(BodyMeasurement.user_id == user.id).order_by(BodyMeasurement.measured_on)).all()
    data = [measurement_to_dict(m, profile) for m in rows]
    headers = ["date", "weight", "body_fat_pct", "waist", "chest", "neck", "left_arm", "right_arm", "hips", "left_thigh", "right_thigh", "notes"]
    return csv_text(headers, [[d.get("measured_on"), d.get("weight"), d.get("body_fat_pct"), d.get("waist"), d.get("chest"), d.get("neck"), d.get("left_arm"), d.get("right_arm"), d.get("hips"), d.get("left_thigh"), d.get("right_thigh"), d.get("notes")] for d in data])


def export_sessions_csv(db: Session, user: User) -> str:
    rows = db.scalars(select(WorkoutSession).where(WorkoutSession.user_id == user.id).order_by(WorkoutSession.scheduled_date)).all()
    return csv_text(
        ["date", "name", "status", "duration_seconds", "source", "notes"],
        [[s.scheduled_date, s.name, s.status, s.duration_seconds, s.source, s.notes] for s in rows],
    )


def export_sets_csv(db: Session, user: User) -> str:
    profile = get_or_create_profile(db, user)
    sessions = db.scalars(
        select(WorkoutSession)
        .options(selectinload(WorkoutSession.exercises).selectinload(PerformedExercise.sets), selectinload(WorkoutSession.exercises).selectinload(PerformedExercise.exercise))
        .where(WorkoutSession.user_id == user.id)
    ).all()
    rows = []
    for s in sessions:
        for ex in s.exercises:
            for st in ex.sets:
                rows.append(
                    [
                        s.scheduled_date,
                        s.name,
                        ex.exercise.name if ex.exercise else "",
                        st.set_number,
                        kg_to_display(st.weight_kg, profile.weight_unit),
                        st.reps,
                        st.rpe,
                        st.completed,
                    ]
                )
    return csv_text(["date", "workout", "exercise", "set", "weight", "reps", "rpe", "completed"], rows)


def export_nutrition_csv(db: Session, user: User) -> str:
    rows = db.scalars(select(NutritionEntry).where(NutritionEntry.user_id == user.id).order_by(NutritionEntry.logged_on)).all()
    return csv_text(
        ["date", "meal", "name", "quantity", "calories", "protein_g", "carbs_g", "fat_g"],
        [[e.logged_on, e.meal, e.name, e.quantity, e.calories, e.protein_g, e.carbs_g, e.fat_g] for e in rows],
    )
