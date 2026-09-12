"""Deterministic workout program generator. No AI. Output is a fully editable starting point."""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.exercise import Exercise
from app.models.profile import UserProfile


WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


@dataclass
class GeneratedSet:
    set_number: int
    set_type: str = "working"
    target_reps: int | None = None
    min_reps: int | None = None
    max_reps: int | None = None
    target_effort: str | None = None
    target_rpe: float | None = None
    rest_seconds: int | None = 90
    target_duration_seconds: int | None = None
    target_distance_m: float | None = None


@dataclass
class GeneratedExercise:
    exercise_id: int
    name: str
    exercise_type: str
    notes: str | None = None
    rest_seconds: int = 90
    sets: list[GeneratedSet] = field(default_factory=list)


@dataclass
class GeneratedWorkout:
    name: str
    weekday: int
    estimated_duration_minutes: int
    exercises: list[GeneratedExercise] = field(default_factory=list)


@dataclass
class GeneratedProgram:
    name: str
    notes: str
    workouts: list[GeneratedWorkout] = field(default_factory=list)


def _find(db: Session, user_id: int, *names: str) -> Exercise | None:
    lowered = [n.lower() for n in names]
    rows = db.scalars(
        select(Exercise).where(
            or_(Exercise.user_id.is_(None), Exercise.user_id == user_id),
            Exercise.is_archived.is_(False),
        )
    ).all()
    by_name = {e.name.lower(): e for e in rows}
    for name in lowered:
        if name in by_name:
            return by_name[name]
    for name in lowered:
        for e in rows:
            if name in e.name.lower():
                return e
    return None


def _equipment_ok(exercise: Exercise, allowed: set[str]) -> bool:
    eq = [str(x).lower() for x in (exercise.equipment or [])]
    if not eq:
        return True
    mapping = {
        "barbell": {"barbell"},
        "dumbbell": {"dumbbell", "dumbbells"},
        "machine": {"machine", "machines"},
        "cable": {"cable", "cable machines"},
        "body only": {"bodyweight", "body only", "none"},
        "other": {"other", "gym", "home"},
        "bands": {"bands", "other"},
    }
    for item in eq:
        aliases = mapping.get(item, {item})
        if aliases & allowed or item in allowed:
            return True
        if "body" in item and ("bodyweight" in allowed or "body only" in allowed):
            return True
    return False


def _strength_sets(n: int, lo: int, hi: int, rest: int, effort: str = "medium", rpe: float = 7) -> list[GeneratedSet]:
    sets: list[GeneratedSet] = []
    for i in range(1, n + 1):
        if i == 1 and n >= 3:
            sets.append(
                GeneratedSet(
                    set_number=i,
                    set_type="warmup",
                    min_reps=lo,
                    max_reps=hi,
                    target_reps=hi,
                    target_effort="light",
                    target_rpe=6,
                    rest_seconds=rest,
                )
            )
        elif i == n and n >= 3:
            sets.append(
                GeneratedSet(
                    set_number=i,
                    set_type="working",
                    min_reps=lo,
                    max_reps=lo,
                    target_reps=lo,
                    target_effort="heavy",
                    target_rpe=8,
                    rest_seconds=rest,
                )
            )
        else:
            sets.append(
                GeneratedSet(
                    set_number=i,
                    set_type="working",
                    min_reps=lo,
                    max_reps=hi,
                    target_reps=hi,
                    target_effort=effort,
                    target_rpe=rpe,
                    rest_seconds=rest,
                )
            )
    return sets


def _bw_sets(n: int, reps: int, rest: int = 90) -> list[GeneratedSet]:
    return [
        GeneratedSet(
            set_number=i,
            target_reps=reps,
            min_reps=max(1, reps - 2),
            max_reps=reps + 2,
            target_effort="medium",
            target_rpe=7,
            rest_seconds=rest,
        )
        for i in range(1, n + 1)
    ]


def _cardio(exercise: Exercise, minutes: int, effort: str = "medium") -> GeneratedExercise:
    return GeneratedExercise(
        exercise_id=exercise.id,
        name=exercise.name,
        exercise_type=exercise.exercise_type,
        rest_seconds=0,
        sets=[],
        notes=f"{minutes} minutes, {effort} effort",
    )


def _pick(db: Session, user_id: int, allowed: set[str], *candidates: tuple[str, ...]) -> Exercise | None:
    for names in candidates:
        found = _find(db, user_id, *names)
        if found and _equipment_ok(found, allowed | {"bodyweight", "body only", "other", "none"}):
            return found
        if found and not found.equipment:
            return found
    for names in candidates:
        found = _find(db, user_id, *names)
        if found:
            return found
    return None


def _ge(ex: Exercise | None, sets: list[GeneratedSet]) -> GeneratedExercise | None:
    if not ex:
        return None
    return GeneratedExercise(
        exercise_id=ex.id,
        name=ex.name,
        exercise_type=ex.exercise_type,
        rest_seconds=sets[0].rest_seconds or 90 if sets else 90,
        sets=sets,
    )


def generate_program(db: Session, user_id: int, profile: UserProfile) -> GeneratedProgram:
    days = max(2, min(profile.days_per_week or 3, 6))
    experience = profile.experience or "beginner"
    goal = profile.primary_goal or "general_fitness"
    duration = profile.typical_duration_minutes or 60
    preferred = list(profile.preferred_days or [])
    if not preferred:
        preferred = [0, 2, 4, 5, 1][:days]
    preferred = preferred[:days]
    while len(preferred) < days:
        for d in range(7):
            if d not in preferred:
                preferred.append(d)
            if len(preferred) >= days:
                break

    equipment = {str(x).lower() for x in (profile.available_equipment or [])}
    locations = {str(x).lower() for x in (profile.available_locations or [])}
    allowed = set(equipment)
    if "gym" in locations:
        allowed.update({"barbell", "dumbbell", "machine", "cable", "other"})
    if "home" in locations:
        allowed.update({"bodyweight", "body only", "dumbbell"})
    if "bodyweight" in equipment or "pull-up bar" in equipment:
        allowed.update({"bodyweight", "body only"})
    if not allowed:
        allowed = {"bodyweight", "body only", "barbell", "dumbbell", "machine"}

    set_count = 3 if experience == "beginner" else 4 if experience == "intermediate" else 5
    if goal == "build_strength":
        rep_lo, rep_hi = 4, 6
        rest = 180
    elif goal == "build_muscle":
        rep_lo, rep_hi = 8, 12
        rest = 90
    elif goal in {"lose_fat", "body_recomposition"}:
        rep_lo, rep_hi = 8, 12
        rest = 75
        set_count = min(set_count, 4)
    elif goal == "improve_endurance":
        rep_lo, rep_hi = 12, 15
        rest = 60
    else:
        rep_lo, rep_hi = 6, 10
        rest = 90

    squat = _pick(db, user_id, allowed, ("barbell squat", "barbell full squat"), ("goblet squat",), ("bodyweight squat", "split squats"))
    hinge = _pick(db, user_id, allowed, ("barbell deadlift",), ("romanian deadlift",), ("dumbbell deadlift",))
    bench = _pick(db, user_id, allowed, ("barbell bench press - medium grip", "bench press"), ("dumbbell bench",), ("pushups", "push-up"))
    row = _pick(db, user_id, allowed, ("bent over barbell row",), ("seated cable rows",), ("one-arm dumbbell row",), ("inverted row",))
    press = _pick(db, user_id, allowed, ("barbell shoulder press", "standing military press", "overhead"), ("dumbbell shoulder press",), ("pushups",))
    pull = _pick(db, user_id, allowed, ("pullups", "weighted pull ups", "chin-up"), ("lat pulldown",), ("inverted row",))
    lunge = _pick(db, user_id, allowed, ("barbell walking lunge",), ("dumbbell lunges",), ("bodyweight walking lunge",))
    rdl = _pick(db, user_id, allowed, ("stiff-legged barbell deadlift", "romanian"), ("dumbbell deadlift",))
    curl = _pick(db, user_id, allowed, ("barbell curl",), ("dumbbell bicep curl", "alternate hammer curl"))
    tri = _pick(db, user_id, allowed, ("parallel bar dip", "dips - triceps version"), ("close-grip barbell bench press",), ("pushups",))
    core = _pick(db, user_id, allowed, ("plank",), ("hanging leg raise",), ("crunches",))
    bike = _pick(db, user_id, allowed, ("bicycling, stationary", "recumbent bike"), ("bicycling",))
    run = _pick(db, user_id, allowed, ("trail running/walking",), ("running, treadmill", "jogging, treadmill"))

    include_cardio = goal in {"lose_fat", "improve_endurance", "general_fitness", "body_recomposition"} or any(
        x in locations or x in equipment for x in ("peloton", "peloton / stationary bike", "running", "outdoor")
    )

    def strength(*items: GeneratedExercise | None) -> list[GeneratedExercise]:
        return [i for i in items if i]

    ss = lambda ex, lo=rep_lo, hi=rep_hi: _ge(ex, _strength_sets(set_count, lo, hi, rest))
    bw = lambda ex, reps=8: _ge(ex, _bw_sets(set_count, reps, rest))

    structure: list[tuple[str, list[GeneratedExercise]]]
    if days <= 2:
        structure = [
            (
                "Full Body A",
                strength(ss(squat), ss(bench), ss(row), bw(pull, 6) if pull and pull.exercise_type == "bodyweight" else ss(pull), _ge(core, _bw_sets(3, 12, 45))),
            ),
            (
                "Full Body B",
                strength(ss(hinge or rdl), ss(press), ss(lunge or squat), ss(tri) or bw(tri, 8), _ge(core, _bw_sets(3, 12, 45))),
            ),
        ]
        name = "2-Day Full Body Program"
    elif days == 3:
        if experience == "beginner":
            structure = [
                ("Full Body A", strength(ss(squat), ss(bench), ss(row), _ge(core, _bw_sets(3, 12, 45)))),
                ("Full Body B", strength(ss(hinge or rdl), ss(press), ss(pull) or bw(pull, 6), _ge(core, _bw_sets(3, 12, 45)))),
                ("Full Body C", strength(ss(lunge or squat), ss(bench), ss(row), ss(tri), _ge(core, _bw_sets(3, 12, 45)))),
            ]
            name = "3-Day Full Body Program"
        else:
            structure = [
                ("Push", strength(ss(bench), ss(press), ss(tri))),
                ("Pull", strength(ss(row), ss(pull) or bw(pull, 6), ss(curl))),
                ("Legs", strength(ss(squat), ss(hinge or rdl), ss(lunge), _ge(core, _bw_sets(3, 12, 45)))),
            ]
            name = "3-Day Push / Pull / Legs"
    elif days == 4:
        structure = [
            ("Upper A", strength(ss(bench), ss(row), ss(press), ss(pull) or bw(pull, 6), ss(curl))),
            ("Lower A", strength(ss(squat), ss(rdl or hinge), ss(lunge), _ge(core, _bw_sets(3, 15, 45)))),
            ("Upper B", strength(ss(press), ss(row), ss(bench), ss(tri), ss(pull) or bw(pull, 6))),
            ("Lower B", strength(ss(hinge or squat), ss(lunge or squat), ss(rdl), _ge(core, _bw_sets(3, 15, 45)))),
        ]
        name = "4-Day Upper / Lower Program"
    else:
        structure = [
            ("Push", strength(ss(bench), ss(press), ss(tri))),
            ("Pull", strength(ss(row), ss(pull) or bw(pull, 6), ss(curl))),
            ("Legs", strength(ss(squat), ss(hinge or rdl), ss(lunge))),
            ("Upper", strength(ss(bench), ss(row), ss(press), ss(pull) or bw(pull, 6))),
            ("Lower", strength(ss(squat), ss(rdl or hinge), _ge(core, _bw_sets(3, 15, 45)))),
        ]
        name = "5-Day Push / Pull / Legs + Upper / Lower"

    if include_cardio:
        cardio_ex = bike if ("peloton" in " ".join(locations | equipment) or "bike" in " ".join(equipment)) else (run or bike)
        minutes = 20 if duration <= 60 else 25
        if cardio_ex:
            for i, (label, exercises) in enumerate(structure):
                if i % 2 == 1 or goal == "improve_endurance":
                    exercises.append(_cardio(cardio_ex, minutes, "medium"))

    workouts: list[GeneratedWorkout] = []
    for i, (label, exercises) in enumerate(structure[:days]):
        weekday = preferred[i]
        day_name = WEEKDAY_NAMES[weekday]
        workouts.append(
            GeneratedWorkout(
                name=f"{day_name} — {label}",
                weekday=weekday,
                estimated_duration_minutes=duration,
                exercises=exercises,
            )
        )

    notes = (
        "Generated from your onboarding settings using deterministic templates. "
        "Edit any workout, exercise, set, or day. Nothing is locked. "
        f"Goal: {goal.replace('_', ' ')}. Experience: {experience}. Days: {days}."
    )
    return GeneratedProgram(name=name, notes=notes, workouts=workouts)
