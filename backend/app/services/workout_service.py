from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.models.user import User
from app.models.program import ProgramWorkout
from app.models.session import WorkoutSession
from app.models.workout import PrescribedSet, WorkoutTemplate, WorkoutTemplateExercise
from app.schemas.training import PrescribedSetIn, TemplateExerciseIn, WorkoutTemplateIn
from app.services.exercise_seed import serialize_exercise
from app.services.units_service import from_kg, get_or_create_profile, to_kg


def serialize_set(row: PrescribedSet, profile) -> dict:
    return {
        "id": row.id,
        "set_number": row.set_number,
        "set_type": row.set_type,
        "target_reps": row.target_reps,
        "min_reps": row.min_reps,
        "max_reps": row.max_reps,
        "target_effort": row.target_effort,
        "target_rpe": row.target_rpe,
        "rest_seconds": row.rest_seconds,
        "target_weight": from_kg(row.target_weight_kg, profile),
        "target_duration_seconds": row.target_duration_seconds,
        "target_distance_m": row.target_distance_m,
        "notes": row.notes,
    }


def serialize_template(template: WorkoutTemplate, profile) -> dict:
    exercises = []
    for item in sorted(template.exercises, key=lambda x: x.position):
        exercises.append(
            {
                "id": item.id,
                "exercise_id": item.exercise_id,
                "position": item.position,
                "notes": item.notes,
                "rest_seconds": item.rest_seconds,
                "exercise": serialize_exercise(item.exercise) if item.exercise else None,
                "sets": [serialize_set(s, profile) for s in sorted(item.sets, key=lambda x: x.set_number)],
            }
        )
    return {
        "id": template.id,
        "name": template.name,
        "notes": template.notes,
        "estimated_duration_minutes": template.estimated_duration_minutes,
        "created_from": template.created_from,
        "exercises": exercises,
    }


def _load_template(db: Session, template_id: int) -> WorkoutTemplate | None:
    return db.scalars(
        select(WorkoutTemplate)
        .options(
            selectinload(WorkoutTemplate.exercises).selectinload(WorkoutTemplateExercise.sets),
            selectinload(WorkoutTemplate.exercises).selectinload(WorkoutTemplateExercise.exercise),
        )
        .where(WorkoutTemplate.id == template_id)
    ).first()


def list_templates(db: Session, user: User) -> list[dict]:
    profile = get_or_create_profile(db, user)
    rows = db.scalars(
        select(WorkoutTemplate)
        .options(
            selectinload(WorkoutTemplate.exercises).selectinload(WorkoutTemplateExercise.sets),
            selectinload(WorkoutTemplate.exercises).selectinload(WorkoutTemplateExercise.exercise),
        )
        .where(WorkoutTemplate.user_id == user.id)
        .order_by(WorkoutTemplate.name.asc())
    ).all()
    return [serialize_template(t, profile) for t in rows]


def get_template(db: Session, user: User, template_id: int) -> dict:
    profile = get_or_create_profile(db, user)
    template = _load_template(db, template_id)
    if not template or template.user_id != user.id:
        raise HTTPException(404, "Workout not found")
    return serialize_template(template, profile)


def _replace_exercises(db: Session, template: WorkoutTemplate, payload: WorkoutTemplateIn, profile) -> None:
    template.exercises.clear()
    db.flush()
    if not payload.exercises:
        return
    for idx, item in enumerate(payload.exercises):
        te = WorkoutTemplateExercise(
            exercise_id=item.exercise_id,
            position=item.position if item.position is not None else idx,
            notes=item.notes,
            rest_seconds=item.rest_seconds,
        )
        sets = item.sets or [PrescribedSetIn(set_number=1, target_reps=8, rest_seconds=item.rest_seconds or 90)]
        for sidx, s in enumerate(sets):
            te.sets.append(
                PrescribedSet(
                    set_number=s.set_number or sidx + 1,
                    set_type=s.set_type,
                    target_reps=s.target_reps,
                    min_reps=s.min_reps,
                    max_reps=s.max_reps,
                    target_effort=s.target_effort,
                    target_rpe=s.target_rpe,
                    rest_seconds=s.rest_seconds if s.rest_seconds is not None else item.rest_seconds,
                    target_weight_kg=to_kg(s.target_weight, profile),
                    target_duration_seconds=s.target_duration_seconds,
                    target_distance_m=s.target_distance_m,
                    notes=s.notes,
                )
            )
        template.exercises.append(te)


def create_template(db: Session, user: User, payload: WorkoutTemplateIn, created_from: str = "manual") -> dict:
    profile = get_or_create_profile(db, user)
    template = WorkoutTemplate(
        user_id=user.id,
        name=payload.name,
        notes=payload.notes,
        estimated_duration_minutes=payload.estimated_duration_minutes,
        created_from=created_from,
    )
    db.add(template)
    db.flush()
    _replace_exercises(db, template, payload, profile)
    db.commit()
    return get_template(db, user, template.id)


def update_template(db: Session, user: User, template_id: int, payload: WorkoutTemplateIn) -> dict:
    profile = get_or_create_profile(db, user)
    template = _load_template(db, template_id)
    if not template or template.user_id != user.id:
        raise HTTPException(404, "Workout not found")
    template.name = payload.name
    template.notes = payload.notes
    if payload.estimated_duration_minutes is not None:
        template.estimated_duration_minutes = payload.estimated_duration_minutes
    if payload.exercises is not None:
        _replace_exercises(db, template, payload, profile)
    db.commit()
    return get_template(db, user, template.id)


def delete_template(db: Session, user: User, template_id: int) -> None:
    template = db.get(WorkoutTemplate, template_id)
    if not template or template.user_id != user.id:
        raise HTTPException(404, "Workout not found")

    # Remove program references to this template.
    db.execute(
        delete(ProgramWorkout).where(ProgramWorkout.template_id == template_id)
    )

    # Preserve workout history while removing the template reference.
    db.query(WorkoutSession).filter(
        WorkoutSession.template_id == template_id
    ).update(
        {WorkoutSession.template_id: None},
        synchronize_session=False,
    )

    db.delete(template)
    db.commit()


def duplicate_template(db: Session, user: User, template_id: int) -> dict:
    original = get_template(db, user, template_id)
    payload = WorkoutTemplateIn(
        name=f"{original['name']} (copy)",
        notes=original.get("notes"),
        estimated_duration_minutes=original.get("estimated_duration_minutes"),
        exercises=[
            TemplateExerciseIn(
                exercise_id=ex["exercise_id"],
                position=ex["position"],
                notes=ex.get("notes"),
                rest_seconds=ex.get("rest_seconds"),
                sets=[PrescribedSetIn(**{k: s.get(k) for k in PrescribedSetIn.model_fields}) for s in ex["sets"]],
            )
            for ex in original["exercises"]
        ],
    )
    return create_template(db, user, payload, created_from="manual")
