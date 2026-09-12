from datetime import date, datetime

from pydantic import BaseModel, Field

from app.schemas.auth import ORMModel


class MeasurementIn(BaseModel):
    measured_on: date | None = None
    weight: float | None = Field(default=None, ge=0)
    body_fat_pct: float | None = Field(default=None, ge=0, le=80)
    waist: float | None = Field(default=None, ge=0)
    chest: float | None = Field(default=None, ge=0)
    neck: float | None = Field(default=None, ge=0)
    left_arm: float | None = Field(default=None, ge=0)
    right_arm: float | None = Field(default=None, ge=0)
    hips: float | None = Field(default=None, ge=0)
    left_thigh: float | None = Field(default=None, ge=0)
    right_thigh: float | None = Field(default=None, ge=0)
    left_calf: float | None = Field(default=None, ge=0)
    right_calf: float | None = Field(default=None, ge=0)
    notes: str | None = None


class MeasurementOut(ORMModel):
    id: int
    measured_on: date
    weight: float | None
    body_fat_pct: float | None
    waist: float | None
    chest: float | None
    neck: float | None
    left_arm: float | None
    right_arm: float | None
    hips: float | None
    left_thigh: float | None
    right_thigh: float | None
    left_calf: float | None
    right_calf: float | None
    notes: str | None
    source: str
    created_at: datetime
    previous: dict[str, float | None] | None = None
    change: dict[str, float | None] | None = None
    change_from_start: dict[str, float | None] | None = None


class GoalIn(BaseModel):
    type: str
    name: str = Field(min_length=1, max_length=200)
    start_value: float | None = None
    current_value: float | None = None
    target_value: float | None = None
    unit: str | None = None
    start_date: date | None = None
    target_date: date | None = None
    status: str | None = None
    measurement_field: str | None = None
    exercise_id: int | None = None
    notes: str | None = None


class GoalOut(ORMModel):
    id: int
    type: str
    name: str
    start_value: float | None
    current_value: float | None
    target_value: float | None
    unit: str | None
    start_date: date
    target_date: date | None
    status: str
    measurement_field: str | None
    exercise_id: int | None
    notes: str | None
    progress_pct: float | None = None
