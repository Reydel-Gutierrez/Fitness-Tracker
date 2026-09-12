from datetime import date, datetime

from pydantic import BaseModel, Field

from app.schemas.auth import ORMModel
from app.schemas.training import ExerciseOut


class SessionCreateIn(BaseModel):
    template_id: int | None = None
    program_id: int | None = None
    name: str | None = None
    scheduled_date: date | None = None
    source: str | None = None
    notes: str | None = None
    exercise_ids: list[int] | None = None


class PerformedSetIn(BaseModel):
    weight: float | None = Field(default=None, ge=0)
    reps: int | None = Field(default=None, ge=0)
    rpe: float | None = Field(default=None, ge=0, le=10)
    added_weight: float | None = Field(default=None, ge=0)
    assisted_weight: float | None = Field(default=None, ge=0)
    completed: bool | None = None
    skipped: bool | None = None
    rest_seconds: int | None = Field(default=None, ge=0)
    notes: str | None = None
    set_type: str | None = None
    target_reps: int | None = None
    target_effort: str | None = None
    target_rpe: float | None = None
    target_weight: float | None = None
    min_reps: int | None = None
    max_reps: int | None = None


class CardioIn(BaseModel):
    duration_seconds: int | None = Field(default=None, ge=0)
    distance_m: float | None = Field(default=None, ge=0)
    calories: float | None = Field(default=None, ge=0)
    avg_hr: int | None = Field(default=None, ge=0, le=250)
    resistance: str | None = None
    rpe: float | None = Field(default=None, ge=0, le=10)
    notes: str | None = None
    completed: bool | None = None


class PerformedSetOut(ORMModel):
    id: int
    set_number: int
    set_type: str
    weight: float | None = None
    reps: int | None
    rpe: float | None
    added_weight: float | None = None
    assisted_weight: float | None = None
    completed: bool
    skipped: bool
    completed_at: datetime | None
    rest_seconds: int | None
    notes: str | None
    target_reps: int | None
    min_reps: int | None
    max_reps: int | None
    target_effort: str | None
    target_rpe: float | None
    target_weight: float | None = None


class CardioOut(ORMModel):
    id: int
    duration_seconds: int | None
    distance_m: float | None
    calories: float | None
    avg_hr: int | None
    resistance: str | None
    rpe: float | None
    notes: str | None
    completed: bool
    target_duration_seconds: int | None
    target_distance_m: float | None
    target_effort: str | None
    pace_sec_per_km: float | None = None


class PreviousSetOut(BaseModel):
    set_number: int
    weight: float | None = None
    reps: int | None = None
    rpe: float | None = None
    completed: bool = False


class PerformedExerciseOut(ORMModel):
    id: int
    exercise_id: int
    position: int
    notes: str | None
    skipped: bool
    exercise: ExerciseOut | None = None
    sets: list[PerformedSetOut] = Field(default_factory=list)
    cardio: CardioOut | None = None
    previous_date: date | None = None
    previous_sets: list[PreviousSetOut] = Field(default_factory=list)
    previous_cardio: CardioOut | None = None
    suggestion: dict | None = None


class WorkoutSessionOut(ORMModel):
    id: int
    name: str
    scheduled_date: date
    started_at: datetime | None
    completed_at: datetime | None
    status: str
    source: str
    notes: str | None
    duration_seconds: int | None
    template_id: int | None
    program_id: int | None
    exercises: list[PerformedExerciseOut] = Field(default_factory=list)
    total_volume: float | None = None
    prs: list[str] = Field(default_factory=list)


class SessionSummaryOut(ORMModel):
    id: int
    name: str
    scheduled_date: date
    status: str
    source: str
    duration_seconds: int | None
    exercise_count: int = 0
    total_volume: float | None = None
