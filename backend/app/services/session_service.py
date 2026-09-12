from datetime import date, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.analytics.calculations import epley_1rm, set_volume
from app.lib.time import utcnow
from app.lib.units import pace_sec_per_km
from app.models.checkin import ProgressionRecommendation
from app.models.exercise import Exercise
from app.models.session import CardioPerformance, PerformedExercise, PerformedSet, WorkoutSession
from app.models.user import User
from app.models.workout import WorkoutTemplate
from app.progression.engine import recommend_strength
from app.schemas.session import CardioIn, PerformedSetIn, SessionCreateIn
from app.services.exercise_seed import serialize_exercise
from app.services.units_service import from_kg, get_or_create_profile, to_kg
from app.services.workout_service import _load_template


def _session_query(db: Session):
    return select(WorkoutSession).options(
        selectinload(WorkoutSession.exercises).selectinload(PerformedExercise.sets),
        selectinload(WorkoutSession.exercises).selectinload(PerformedExercise.cardio),
        selectinload(WorkoutSession.exercises).selectinload(PerformedExercise.exercise),
    )


def _volume_for_session(session: WorkoutSession) -> float:
    total = 0.0
    for ex in session.exercises:
        for s in ex.sets:
            if s.completed and not s.skipped:
                w = s.weight_kg if s.weight_kg is not None else s.added_weight_kg
                total += set_volume(w, s.reps)
    return total


def _previous_for_exercise(db: Session, user_id: int, exercise_id: int, before: WorkoutSession) -> PerformedExercise | None:
    sessions = db.scalars(
        select(WorkoutSession)
        .options(
            selectinload(WorkoutSession.exercises).selectinload(PerformedExercise.sets),
            selectinload(WorkoutSession.exercises).selectinload(PerformedExercise.cardio),
        )
        .where(
            WorkoutSession.user_id == user_id,
            WorkoutSession.status == "completed",
            WorkoutSession.id != before.id,
        )
        .order_by(WorkoutSession.scheduled_date.desc(), WorkoutSession.id.desc())
    ).all()
    for sess in sessions:
        for ex in sess.exercises:
            if ex.exercise_id == exercise_id and not ex.skipped:
                return ex
    return None


def _prs_for_session(db: Session, user: User, session: WorkoutSession, profile) -> list[str]:
    messages: list[str] = []
    for ex in session.exercises:
        if ex.skipped:
            continue
        hist = db.scalars(
            select(PerformedSet)
            .join(PerformedExercise)
            .join(WorkoutSession)
            .where(
                WorkoutSession.user_id == user.id,
                WorkoutSession.status == "completed",
                WorkoutSession.id != session.id,
                PerformedExercise.exercise_id == ex.exercise_id,
                PerformedSet.completed.is_(True),
            )
        ).all()
        hist_weights = [s.weight_kg for s in hist if s.weight_kg]
        hist_1rms = [epley_1rm(s.weight_kg, s.reps) for s in hist if s.weight_kg and s.reps]
        hist_1rms = [x for x in hist_1rms if x]
        hist_volume = 0.0
        # per previous session volume skipped for simplicity; session volume PR later
        best_weight = max(hist_weights) if hist_weights else 0
        best_1rm = max(hist_1rms) if hist_1rms else 0
        for s in ex.sets:
            if not s.completed or s.skipped:
                continue
            if s.weight_kg and s.weight_kg > best_weight:
                messages.append(f"PR — heaviest {ex.exercise.name if ex.exercise else 'lift'}: {from_kg(s.weight_kg, profile)}")
                best_weight = s.weight_kg
            est = epley_1rm(s.weight_kg or 0, s.reps or 0)
            if est and est > best_1rm:
                messages.append(
                    f"PR — estimated 1RM {ex.exercise.name if ex.exercise else 'lift'}: {from_kg(est, profile)}"
                )
                best_1rm = est
            if s.weight_kg and s.reps:
                same = [h for h in hist if h.weight_kg == s.weight_kg and (h.reps or 0) > 0]
                best_reps = max((h.reps or 0) for h in same) if same else 0
                if s.reps > best_reps and best_reps > 0:
                    messages.append(
                        f"PR — {from_kg(s.weight_kg, profile)} × {s.reps} {ex.exercise.name if ex.exercise else ''}".strip()
                    )
    return list(dict.fromkeys(messages))


def serialize_cardio(cardio: CardioPerformance | None) -> dict | None:
    if not cardio:
        return None
    return {
        "id": cardio.id,
        "duration_seconds": cardio.duration_seconds,
        "distance_m": cardio.distance_m,
        "calories": cardio.calories,
        "avg_hr": cardio.avg_hr,
        "resistance": cardio.resistance,
        "rpe": cardio.rpe,
        "notes": cardio.notes,
        "completed": cardio.completed,
        "target_duration_seconds": cardio.target_duration_seconds,
        "target_distance_m": cardio.target_distance_m,
        "target_effort": cardio.target_effort,
        "pace_sec_per_km": pace_sec_per_km(cardio.duration_seconds, cardio.distance_m),
    }


def serialize_session(db: Session, user: User, session: WorkoutSession, include_previous: bool = True) -> dict:
    profile = get_or_create_profile(db, user)
    exercises = []
    for ex in sorted(session.exercises, key=lambda x: x.position):
        prev = _previous_for_exercise(db, user.id, ex.exercise_id, session) if include_previous else None
        suggestion = None
        pending = db.scalars(
            select(ProgressionRecommendation)
            .where(
                ProgressionRecommendation.user_id == user.id,
                ProgressionRecommendation.exercise_id == ex.exercise_id,
                ProgressionRecommendation.status == "pending",
            )
            .order_by(ProgressionRecommendation.created_at.desc())
        ).first()
        if pending:
            suggestion = {
                "id": pending.id,
                "suggested_weight": from_kg(pending.suggested_weight_kg, profile),
                "suggested_reps": pending.suggested_reps,
                "reason": pending.reason,
                "status": pending.status,
            }
        exercises.append(
            {
                "id": ex.id,
                "exercise_id": ex.exercise_id,
                "position": ex.position,
                "notes": ex.notes,
                "skipped": ex.skipped,
                "exercise": serialize_exercise(ex.exercise) if ex.exercise else None,
                "sets": [
                    {
                        "id": s.id,
                        "set_number": s.set_number,
                        "set_type": s.set_type,
                        "weight": from_kg(s.weight_kg, profile),
                        "reps": s.reps,
                        "rpe": s.rpe,
                        "added_weight": from_kg(s.added_weight_kg, profile),
                        "assisted_weight": from_kg(s.assisted_weight_kg, profile),
                        "completed": s.completed,
                        "skipped": s.skipped,
                        "completed_at": s.completed_at,
                        "rest_seconds": s.rest_seconds,
                        "notes": s.notes,
                        "target_reps": s.target_reps,
                        "min_reps": s.min_reps,
                        "max_reps": s.max_reps,
                        "target_effort": s.target_effort,
                        "target_rpe": s.target_rpe,
                        "target_weight": from_kg(s.target_weight_kg, profile),
                    }
                    for s in sorted(ex.sets, key=lambda x: x.set_number)
                ],
                "cardio": serialize_cardio(ex.cardio),
                "previous_date": prev.session.scheduled_date if prev and prev.session else None,
                "previous_sets": [
                    {
                        "set_number": s.set_number,
                        "weight": from_kg(s.weight_kg, profile),
                        "reps": s.reps,
                        "rpe": s.rpe,
                        "completed": s.completed,
                    }
                    for s in sorted(prev.sets, key=lambda x: x.set_number)
                ]
                if prev
                else [],
                "previous_cardio": serialize_cardio(prev.cardio) if prev else None,
                "suggestion": suggestion,
            }
        )
    return {
        "id": session.id,
        "name": session.name,
        "scheduled_date": session.scheduled_date,
        "started_at": session.started_at,
        "completed_at": session.completed_at,
        "status": session.status,
        "source": session.source,
        "notes": session.notes,
        "duration_seconds": session.duration_seconds,
        "template_id": session.template_id,
        "program_id": session.program_id,
        "exercises": exercises,
        "total_volume": from_kg(_volume_for_session(session), profile) if _volume_for_session(session) else 0,
        "prs": _prs_for_session(db, user, session, profile) if session.status == "completed" else [],
    }


def get_session(db: Session, user: User, session_id: int) -> dict:
    session = db.scalars(_session_query(db).where(WorkoutSession.id == session_id)).first()
    if not session or session.user_id != user.id:
        raise HTTPException(404, "Session not found")
    return serialize_session(db, user, session)


def _clone_from_template(db: Session, session: WorkoutSession, template: WorkoutTemplate) -> None:
    for idx, item in enumerate(sorted(template.exercises, key=lambda x: x.position)):
        pe = PerformedExercise(
            exercise_id=item.exercise_id,
            original_exercise_id=item.exercise_id,
            position=idx,
            notes=item.notes,
        )
        exercise = db.get(Exercise, item.exercise_id)
        etype = exercise.exercise_type if exercise else "strength"
        if etype in {"cardio", "timed", "distance"}:
            first = item.sets[0] if item.sets else None
            pe.cardio = CardioPerformance(
                target_duration_seconds=first.target_duration_seconds if first else None,
                target_distance_m=first.target_distance_m if first else None,
                target_effort=first.target_effort if first else None,
            )
        else:
            for s in sorted(item.sets, key=lambda x: x.set_number):
                pe.sets.append(
                    PerformedSet(
                        set_number=s.set_number,
                        set_type=s.set_type,
                        target_reps=s.target_reps,
                        min_reps=s.min_reps,
                        max_reps=s.max_reps,
                        target_effort=s.target_effort,
                        target_rpe=s.target_rpe,
                        rest_seconds=s.rest_seconds if s.rest_seconds is not None else item.rest_seconds,
                        target_weight_kg=s.target_weight_kg,
                        weight_kg=s.target_weight_kg,
                        reps=s.target_reps,
                    )
                )
            if not item.sets:
                pe.sets.append(PerformedSet(set_number=1, set_type="working", target_reps=8, rest_seconds=90))
        session.exercises.append(pe)


def start_session(db: Session, user: User, payload: SessionCreateIn) -> dict:
    existing = db.scalars(
        select(WorkoutSession).where(WorkoutSession.user_id == user.id, WorkoutSession.status == "in_progress")
    ).first()
    if existing and not payload.template_id and not payload.exercise_ids and not payload.name:
        return get_session(db, user, existing.id)

    name = payload.name or "Quick Workout"
    template = None
    if payload.template_id:
        template = _load_template(db, payload.template_id)
        if not template or template.user_id != user.id:
            raise HTTPException(404, "Workout not found")
        name = template.name
    session = WorkoutSession(
        user_id=user.id,
        template_id=payload.template_id,
        program_id=payload.program_id,
        name=name,
        scheduled_date=payload.scheduled_date or date.today(),
        started_at=utcnow(),
        status="in_progress",
        source=payload.source or ("quick" if not payload.template_id else "scheduled"),
        notes=payload.notes,
    )
    db.add(session)
    db.flush()
    if template:
        _clone_from_template(db, session, template)
    for idx, eid in enumerate(payload.exercise_ids or []):
        exercise = db.get(Exercise, eid)
        if not exercise:
            continue
        pe = PerformedExercise(exercise_id=eid, original_exercise_id=eid, position=len(session.exercises) + idx)
        if exercise.exercise_type in {"cardio", "timed", "distance"}:
            pe.cardio = CardioPerformance()
        else:
            pe.sets.append(PerformedSet(set_number=1, set_type="working", target_reps=8, rest_seconds=90))
        session.exercises.append(pe)
    db.commit()
    return get_session(db, user, session.id)


def list_sessions(db: Session, user: User, limit: int = 50) -> list[dict]:
    profile = get_or_create_profile(db, user)
    rows = db.scalars(
        select(WorkoutSession)
        .options(selectinload(WorkoutSession.exercises).selectinload(PerformedExercise.sets))
        .where(WorkoutSession.user_id == user.id)
        .order_by(WorkoutSession.scheduled_date.desc(), WorkoutSession.id.desc())
        .limit(limit)
    ).all()
    out = []
    for s in rows:
        out.append(
            {
                "id": s.id,
                "name": s.name,
                "scheduled_date": s.scheduled_date,
                "status": s.status,
                "source": s.source,
                "duration_seconds": s.duration_seconds,
                "exercise_count": len(s.exercises),
                "total_volume": from_kg(_volume_for_session(s), profile),
            }
        )
    return out


def update_set(db: Session, user: User, session_id: int, set_id: int, payload: PerformedSetIn) -> dict:
    session = db.scalars(_session_query(db).where(WorkoutSession.id == session_id)).first()
    if not session or session.user_id != user.id:
        raise HTTPException(404, "Session not found")
    profile = get_or_create_profile(db, user)
    target = None
    for ex in session.exercises:
        for s in ex.sets:
            if s.id == set_id:
                target = s
                break
    if not target:
        raise HTTPException(404, "Set not found")
    if payload.weight is not None:
        target.weight_kg = to_kg(payload.weight, profile)
    if payload.reps is not None:
        target.reps = payload.reps
    if payload.rpe is not None:
        target.rpe = payload.rpe
    if payload.added_weight is not None:
        target.added_weight_kg = to_kg(payload.added_weight, profile)
    if payload.assisted_weight is not None:
        target.assisted_weight_kg = to_kg(payload.assisted_weight, profile)
    if payload.rest_seconds is not None:
        target.rest_seconds = payload.rest_seconds
    if payload.notes is not None:
        target.notes = payload.notes
    if payload.set_type is not None:
        target.set_type = payload.set_type
    if payload.target_reps is not None:
        target.target_reps = payload.target_reps
    if payload.skipped is True:
        target.skipped = True
        target.completed = False
        target.completed_at = None
    if payload.completed is True:
        target.completed = True
        target.skipped = False
        target.completed_at = utcnow()
    if payload.completed is False and payload.skipped is not True:
        target.completed = False
        target.completed_at = None
    db.commit()
    return get_session(db, user, session_id)


def add_set(db: Session, user: User, session_id: int, exercise_id: int) -> dict:
    session = db.scalars(_session_query(db).where(WorkoutSession.id == session_id)).first()
    if not session or session.user_id != user.id:
        raise HTTPException(404, "Session not found")
    pe = next((e for e in session.exercises if e.id == exercise_id), None)
    if not pe:
        raise HTTPException(404, "Exercise not found")
    last = max((s.set_number for s in pe.sets), default=0)
    last_set = max(pe.sets, key=lambda s: s.set_number, default=None)
    pe.sets.append(
        PerformedSet(
            set_number=last + 1,
            set_type="working",
            target_reps=last_set.target_reps if last_set else 8,
            min_reps=last_set.min_reps if last_set else None,
            max_reps=last_set.max_reps if last_set else None,
            target_effort=last_set.target_effort if last_set else None,
            target_rpe=last_set.target_rpe if last_set else None,
            rest_seconds=last_set.rest_seconds if last_set else 90,
            weight_kg=last_set.weight_kg if last_set else None,
            reps=last_set.target_reps if last_set else 8,
        )
    )
    db.commit()
    return get_session(db, user, session_id)


def remove_set(db: Session, user: User, session_id: int, set_id: int) -> dict:
    session = db.scalars(_session_query(db).where(WorkoutSession.id == session_id)).first()
    if not session or session.user_id != user.id:
        raise HTTPException(404, "Session not found")
    for ex in session.exercises:
        for s in list(ex.sets):
            if s.id == set_id:
                ex.sets.remove(s)
                for i, remaining in enumerate(sorted(ex.sets, key=lambda x: x.set_number), start=1):
                    remaining.set_number = i
                db.commit()
                return get_session(db, user, session_id)
    raise HTTPException(404, "Set not found")


def update_cardio(db: Session, user: User, session_id: int, exercise_id: int, payload: CardioIn) -> dict:
    session = db.scalars(_session_query(db).where(WorkoutSession.id == session_id)).first()
    if not session or session.user_id != user.id:
        raise HTTPException(404, "Session not found")
    pe = next((e for e in session.exercises if e.id == exercise_id), None)
    if not pe:
        raise HTTPException(404, "Exercise not found")
    if not pe.cardio:
        pe.cardio = CardioPerformance()
    for field in ("duration_seconds", "distance_m", "calories", "avg_hr", "resistance", "rpe", "notes", "completed"):
        value = getattr(payload, field)
        if value is not None:
            setattr(pe.cardio, field, value)
    db.commit()
    return get_session(db, user, session_id)


def add_exercise(db: Session, user: User, session_id: int, exercise_id: int) -> dict:
    session = db.scalars(_session_query(db).where(WorkoutSession.id == session_id)).first()
    if not session or session.user_id != user.id:
        raise HTTPException(404, "Session not found")
    exercise = db.get(Exercise, exercise_id)
    if not exercise:
        raise HTTPException(404, "Exercise not found")
    pe = PerformedExercise(
        exercise_id=exercise_id,
        original_exercise_id=exercise_id,
        position=len(session.exercises),
    )
    if exercise.exercise_type in {"cardio", "timed", "distance"}:
        pe.cardio = CardioPerformance()
    else:
        pe.sets.append(PerformedSet(set_number=1, set_type="working", target_reps=8, rest_seconds=90, reps=8))
    session.exercises.append(pe)
    db.commit()
    return get_session(db, user, session_id)


def replace_exercise(db: Session, user: User, session_id: int, performed_id: int, exercise_id: int) -> dict:
    session = db.scalars(_session_query(db).where(WorkoutSession.id == session_id)).first()
    if not session or session.user_id != user.id:
        raise HTTPException(404, "Session not found")
    pe = next((e for e in session.exercises if e.id == performed_id), None)
    if not pe:
        raise HTTPException(404, "Exercise not found")
    exercise = db.get(Exercise, exercise_id)
    if not exercise:
        raise HTTPException(404, "Replacement exercise not found")
    pe.original_exercise_id = pe.original_exercise_id or pe.exercise_id
    pe.exercise_id = exercise_id
    pe.sets.clear()
    pe.cardio = None
    if exercise.exercise_type in {"cardio", "timed", "distance"}:
        pe.cardio = CardioPerformance()
    else:
        pe.sets.append(PerformedSet(set_number=1, set_type="working", target_reps=8, rest_seconds=90, reps=8))
    db.commit()
    return get_session(db, user, session_id)


def skip_exercise(db: Session, user: User, session_id: int, performed_id: int) -> dict:
    session = db.scalars(_session_query(db).where(WorkoutSession.id == session_id)).first()
    if not session or session.user_id != user.id:
        raise HTTPException(404, "Session not found")
    pe = next((e for e in session.exercises if e.id == performed_id), None)
    if not pe:
        raise HTTPException(404, "Exercise not found")
    pe.skipped = not pe.skipped
    db.commit()
    return get_session(db, user, session_id)


def update_exercise_notes(db: Session, user: User, session_id: int, performed_id: int, notes: str | None) -> dict:
    session = db.scalars(_session_query(db).where(WorkoutSession.id == session_id)).first()
    if not session or session.user_id != user.id:
        raise HTTPException(404, "Session not found")
    pe = next((e for e in session.exercises if e.id == performed_id), None)
    if not pe:
        raise HTTPException(404, "Exercise not found")
    pe.notes = notes
    db.commit()
    return get_session(db, user, session_id)


def finish_session(db: Session, user: User, session_id: int, notes: str | None = None) -> dict:
    session = db.scalars(_session_query(db).where(WorkoutSession.id == session_id)).first()
    if not session or session.user_id != user.id:
        raise HTTPException(404, "Session not found")
    session.status = "completed"
    session.completed_at = utcnow()
    if notes is not None:
        session.notes = notes
    if session.started_at:
        start = session.started_at
        if start.tzinfo is None:
            from datetime import timezone

            start = start.replace(tzinfo=timezone.utc)
        session.duration_seconds = int((utcnow() - start).total_seconds())
    profile = get_or_create_profile(db, user)
    increment = 2.5 if profile.weight_unit == "kg" else 5.0 / 2.2046226218
    for ex in session.exercises:
        if ex.skipped or not ex.sets:
            continue
        working = [s for s in ex.sets if s.set_type != "warmup" and s.completed and not s.skipped]
        if not working:
            working = [s for s in ex.sets if s.completed and not s.skipped]
        if not working:
            continue
        result = recommend_strength(
            completed_reps=[s.reps or 0 for s in working],
            target_reps=[s.target_reps for s in working],
            actual_rpe=[s.rpe for s in working],
            target_rpe=[s.target_rpe for s in working],
            last_weight=working[-1].weight_kg or working[-1].added_weight_kg,
            increment=increment,
        )
        if result.suggested_weight is not None:
            db.add(
                ProgressionRecommendation(
                    user_id=user.id,
                    exercise_id=ex.exercise_id,
                    session_id=session.id,
                    suggested_weight_kg=result.suggested_weight,
                    suggested_reps=result.suggested_reps,
                    reason=result.reason,
                    status="pending",
                )
            )
    db.commit()
    return get_session(db, user, session_id)


def active_session(db: Session, user: User) -> dict | None:
    session = db.scalars(
        _session_query(db).where(WorkoutSession.user_id == user.id, WorkoutSession.status == "in_progress")
    ).first()
    if not session:
        return None
    return serialize_session(db, user, session)


def calendar_items(db: Session, user: User, start: date, end: date) -> list[dict]:
    sessions = db.scalars(
        select(WorkoutSession).where(
            WorkoutSession.user_id == user.id,
            WorkoutSession.scheduled_date >= start,
            WorkoutSession.scheduled_date <= end,
        )
    ).all()
    from app.services.program_service import active_program

    program = active_program(db, user)
    scheduled = []
    if program:
        cur = start
        while cur <= end:
            for w in program["workouts"]:
                if w["weekday"] == cur.weekday():
                    existing = next((s for s in sessions if s.scheduled_date == cur and s.template_id == w["template_id"]), None)
                    status = existing.status if existing else ("missed" if cur < date.today() else "scheduled")
                    scheduled.append(
                        {
                            "date": cur.isoformat(),
                            "name": (w.get("template") or {}).get("name") or w.get("name_override") or "Workout",
                            "status": status,
                            "session_id": existing.id if existing else None,
                            "template_id": w["template_id"],
                            "kind": "scheduled" if not existing else existing.status,
                        }
                    )
            cur += timedelta(days=1)
    extras = []
    for s in sessions:
        if not any(x.get("session_id") == s.id for x in scheduled):
            extras.append(
                {
                    "date": s.scheduled_date.isoformat(),
                    "name": s.name,
                    "status": s.status,
                    "session_id": s.id,
                    "template_id": s.template_id,
                    "kind": "unscheduled" if s.source in {"quick", "extra"} else s.status,
                }
            )
    return scheduled + extras


def respond_recommendation(db: Session, user: User, rec_id: int, status: str) -> dict:
    rec = db.get(ProgressionRecommendation, rec_id)
    if not rec or rec.user_id != user.id:
        raise HTTPException(404, "Recommendation not found")
    rec.status = status
    db.commit()
    return {"id": rec.id, "status": rec.status, "reason": rec.reason}
