from datetime import date, datetime

from pydantic import BaseModel, Field

from app.schemas.auth import ORMModel
from app.schemas.body import MeasurementIn


class FoodIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    serving_description: str = "1 serving"
    calories: float = Field(ge=0)
    protein_g: float = Field(default=0, ge=0)
    carbs_g: float = Field(default=0, ge=0)
    fat_g: float = Field(default=0, ge=0)
    fiber_g: float | None = Field(default=None, ge=0)


class FoodOut(ORMModel):
    id: int
    name: str
    serving_description: str
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float | None
    use_count: int
    source: str


class NutritionEntryIn(BaseModel):
    logged_on: date | None = None
    meal: str = "snack"
    name: str | None = None
    food_id: int | None = None
    quantity: float = Field(default=1, ge=0)
    calories: float | None = Field(default=None, ge=0)
    protein_g: float | None = Field(default=None, ge=0)
    carbs_g: float | None = Field(default=None, ge=0)
    fat_g: float | None = Field(default=None, ge=0)
    fiber_g: float | None = Field(default=None, ge=0)
    serving_description: str | None = None


class NutritionEntryOut(ORMModel):
    id: int
    logged_on: date
    meal: str
    name: str
    food_id: int | None
    quantity: float
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float | None


class NutritionTargetIn(BaseModel):
    calories: float = Field(ge=0)
    protein_g: float = Field(ge=0)
    carbs_g: float = Field(ge=0)
    fat_g: float = Field(ge=0)


class NutritionTargetOut(ORMModel):
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float


class DayNutritionOut(BaseModel):
    date: date
    entries: list[NutritionEntryOut]
    totals: dict[str, float]
    target: NutritionTargetOut
    consumed_vs_target: dict[str, dict[str, float]]


class CheckInIn(MeasurementIn):
    checkin_date: date | None = None
    energy: int | None = Field(default=None, ge=1, le=5)
    sleep_quality: int | None = Field(default=None, ge=1, le=5)
    stress: int | None = Field(default=None, ge=1, le=5)
    training_satisfaction: int | None = Field(default=None, ge=1, le=5)


class CheckInOut(ORMModel):
    id: int
    week_start: date
    checkin_date: date
    energy: int | None
    sleep_quality: int | None
    stress: int | None
    training_satisfaction: int | None
    notes: str | None
    measurement: dict | None = None
