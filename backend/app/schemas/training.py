from pydantic import BaseModel, Field

from app.schemas.auth import ORMModel


class ExerciseIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    exercise_type: str = "strength"
    instructions: list[str] | str | None = None
    primary_muscles: list[str] = Field(default_factory=list)
    secondary_muscles: list[str] = Field(default_factory=list)
    equipment: list[str] = Field(default_factory=list)
    difficulty: str | None = None
    category: str | None = None
    notes: str | None = None
    images: list[str] = Field(default_factory=list)


class ExerciseOut(ORMModel):
    id: int
    name: str
    source: str
    exercise_type: str
    instructions: list | str | None
    primary_muscles: list
    secondary_muscles: list
    equipment: list
    difficulty: str | None
    category: str | None
    images: list
    thumbnail: str | None = None
    notes: str | None
    is_custom: bool = False


class PrescribedSetIn(BaseModel):
    set_number: int | None = None
    set_type: str = "working"
    target_reps: int | None = Field(default=None, ge=0)
    min_reps: int | None = Field(default=None, ge=0)
    max_reps: int | None = Field(default=None, ge=0)
    target_effort: str | None = None
    target_rpe: float | None = Field(default=None, ge=0, le=10)
    rest_seconds: int | None = Field(default=None, ge=0)
    target_weight: float | None = Field(default=None, ge=0)
    target_duration_seconds: int | None = Field(default=None, ge=0)
    target_distance_m: float | None = Field(default=None, ge=0)
    notes: str | None = None


class TemplateExerciseIn(BaseModel):
    exercise_id: int
    position: int | None = None
    notes: str | None = None
    rest_seconds: int | None = Field(default=90, ge=0)
    sets: list[PrescribedSetIn] = Field(default_factory=list)


class WorkoutTemplateIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    notes: str | None = None
    estimated_duration_minutes: int | None = Field(default=None, ge=0)
    exercises: list[TemplateExerciseIn] | None = None


class PrescribedSetOut(ORMModel):
    id: int
    set_number: int
    set_type: str
    target_reps: int | None
    min_reps: int | None
    max_reps: int | None
    target_effort: str | None
    target_rpe: float | None
    rest_seconds: int | None
    target_weight: float | None = None
    target_duration_seconds: int | None
    target_distance_m: float | None
    notes: str | None


class TemplateExerciseOut(ORMModel):
    id: int
    exercise_id: int
    position: int
    notes: str | None
    rest_seconds: int | None
    exercise: ExerciseOut | None = None
    sets: list[PrescribedSetOut] = Field(default_factory=list)


class WorkoutTemplateOut(ORMModel):
    id: int
    name: str
    notes: str | None
    estimated_duration_minutes: int | None
    created_from: str
    exercises: list[TemplateExerciseOut] = Field(default_factory=list)


class ProgramWorkoutIn(BaseModel):
    template_id: int
    weekday: int = Field(ge=0, le=6)
    position: int | None = None
    name_override: str | None = None


class ProgramIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    notes: str | None = None
    is_active: bool | None = True
    start_date: str | None = None
    workouts: list[ProgramWorkoutIn] | None = None


class ProgramWorkoutOut(ORMModel):
    id: int
    template_id: int
    weekday: int
    position: int
    name_override: str | None
    template: WorkoutTemplateOut | None = None


class ProgramOut(ORMModel):
    id: int
    name: str
    notes: str | None
    is_active: bool
    generated: bool
    workouts: list[ProgramWorkoutOut] = Field(default_factory=list)
