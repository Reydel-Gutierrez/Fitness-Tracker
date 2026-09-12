from datetime import date

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.program import Program, ProgramWorkout
from app.models.session import WorkoutSession
from app.models.user import User
from app.models.workout import WorkoutTemplate
from app.program_generator.generator import generate_program
from app.schemas.training import (
    PrescribedSetIn,
    ProgramIn,
    ProgramWorkoutIn,
    TemplateExerciseIn,
    WorkoutTemplateIn,
)
from app.services.units_service import get_or_create_profile
from app.services.workout_service import create_template, get_template, serialize_template, _load_template


def serialize_program(program: Program, profile) -> dict:
    workouts = []
    for item in sorted(program.workouts, key=lambda x: x.position):
        workouts.append(
            {
                "id": item.id,
                "template_id": item.template_id,
                "weekday": item.weekday,
                "position": item.position,
                "name_override": item.name_override,
                "template": serialize_template(item.template, profile) if item.template else None,
            }
        )
    return {
        "id": program.id,
        "name": program.name,
        "notes": program.notes,
        "is_active": program.is_active,
        "generated": program.generated,
        "workouts": workouts,
    }


def _load_program(db: Session, program_id: int) -> Program | None:
    return db.scalars(
        select(Program)
        .options(
            selectinload(Program.workouts).selectinload(ProgramWorkout.template).selectinload(WorkoutTemplate.exercises)
        )
        .where(Program.id == program_id)
    ).first()


def list_programs(db: Session, user: User) -> list[dict]:
    profile = get_or_create_profile(db, user)
    rows = db.scalars(
        select(Program)
        .options(selectinload(Program.workouts).selectinload(ProgramWorkout.template))
        .where(Program.user_id == user.id)
        .order_by(Program.created_at.desc())
    ).all()
    # load nested template details
    out = []
    for p in rows:
        full = _load_program(db, p.id)
        out.append(serialize_program(full, profile))
    return out


def get_program(db: Session, user: User, program_id: int) -> dict:
    profile = get_or_create_profile(db, user)
    program = _load_program(db, program_id)
    if not program or program.user_id != user.id:
        raise HTTPException(404, "Program not found")
    # ensure exercises/sets loaded
    for pw in program.workouts:
        if pw.template:
            _load_template(db, pw.template_id)
    program = _load_program(db, program_id)
    return serialize_program(program, profile)


def create_program(db: Session, user: User, payload: ProgramIn, generated: bool = False) -> dict:
    if payload.is_active:
        db.query(Program).filter(Program.user_id == user.id, Program.is_active.is_(True)).update({"is_active": False})
    program = Program(
        user_id=user.id,
        name=payload.name,
        notes=payload.notes,
        is_active=True if payload.is_active is None else payload.is_active,
        generated=generated,
        start_date=date.today(),
    )
    db.add(program)
    db.flush()
    for idx, item in enumerate(payload.workouts or []):
        program.workouts.append(
            ProgramWorkout(
                template_id=item.template_id,
                weekday=item.weekday,
                position=item.position if item.position is not None else idx,
                name_override=item.name_override,
            )
        )
    db.commit()
    return get_program(db, user, program.id)


def update_program(db: Session, user: User, program_id: int, payload: ProgramIn) -> dict:
    program = db.get(Program, program_id)
    if not program or program.user_id != user.id:
        raise HTTPException(404, "Program not found")
    program.name = payload.name
    program.notes = payload.notes
    if payload.is_active:
        db.query(Program).filter(Program.user_id == user.id, Program.id != program.id).update({"is_active": False})
        program.is_active = True
    elif payload.is_active is False:
        program.is_active = False
    if payload.workouts is not None:
        program.workouts.clear()
        db.flush()
        for idx, item in enumerate(payload.workouts):
            program.workouts.append(
                ProgramWorkout(
                    template_id=item.template_id,
                    weekday=item.weekday,
                    position=item.position if item.position is not None else idx,
                    name_override=item.name_override,
                )
            )
    db.commit()
    return get_program(db, user, program.id)


def delete_program(db: Session, user: User, program_id: int) -> None:
    program = db.get(Program, program_id)
    if not program or program.user_id != user.id:
        raise HTTPException(404, "Program not found")
    template_ids = list(dict.fromkeys(pw.template_id for pw in program.workouts))
    db.query(WorkoutSession).filter(WorkoutSession.program_id == program.id).update(
        {"program_id": None}, synchronize_session=False
    )
    db.delete(program)
    db.flush()
    for tid in template_ids:
        still_used = db.scalars(
            select(ProgramWorkout.id).where(ProgramWorkout.template_id == tid).limit(1)
        ).first()
        if still_used:
            continue
        db.query(WorkoutSession).filter(WorkoutSession.template_id == tid).update(
            {"template_id": None}, synchronize_session=False
        )
        template = db.get(WorkoutTemplate, tid)
        if template and template.user_id == user.id:
            db.delete(template)
    db.commit()


def generate_and_save(db: Session, user: User) -> dict:
    profile = get_or_create_profile(db, user)
    generated = generate_program(db, user.id, profile)
    template_ids: list[tuple[int, int, str]] = []
    for workout in generated.workouts:
        payload = WorkoutTemplateIn(
            name=workout.name,
            notes=None,
            estimated_duration_minutes=workout.estimated_duration_minutes,
            exercises=[
                TemplateExerciseIn(
                    exercise_id=ex.exercise_id,
                    notes=ex.notes,
                    rest_seconds=ex.rest_seconds,
                    sets=[
                        PrescribedSetIn(
                            set_number=s.set_number,
                            set_type=s.set_type,
                            target_reps=s.target_reps,
                            min_reps=s.min_reps,
                            max_reps=s.max_reps,
                            target_effort=s.target_effort,
                            target_rpe=s.target_rpe,
                            rest_seconds=s.rest_seconds,
                            target_duration_seconds=s.target_duration_seconds,
                            target_distance_m=s.target_distance_m,
                        )
                        for s in s_list
                    ]
                    if (s_list := ex.sets)
                    else (
                        [
                            PrescribedSetIn(
                                set_number=1,
                                target_duration_seconds=20 * 60,
                                target_effort="medium",
                                rest_seconds=0,
                            )
                        ]
                        if ex.exercise_type in {"cardio", "timed", "distance"}
                        else []
                    ),
                )
                for ex in workout.exercises
            ],
        )
        saved = create_template(db, user, payload, created_from="generated")
        template_ids.append((saved["id"], workout.weekday, workout.name))
    program_payload = ProgramIn(
        name=generated.name,
        notes=generated.notes,
        is_active=True,
        workouts=[
            ProgramWorkoutIn(template_id=tid, weekday=wd, position=i)
            for i, (tid, wd, _name) in enumerate(template_ids)
        ],
    )
    return create_program(db, user, program_payload, generated=True)


def active_program(db: Session, user: User) -> dict | None:
    row = db.scalars(select(Program).where(Program.user_id == user.id, Program.is_active.is_(True))).first()
    if not row:
        return None
    return get_program(db, user, row.id)
