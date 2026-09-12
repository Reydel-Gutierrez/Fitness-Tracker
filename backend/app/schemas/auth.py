from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(ORMModel):
    id: int
    email: str
    username: str
    name: str
    created_at: datetime


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)
    name: str = Field(min_length=1, max_length=200)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class ProfileIn(BaseModel):
    name: str | None = None
    date_of_birth: date | None = None
    sex: str | None = None
    height: float | None = Field(default=None, ge=0)
    primary_goal: str | None = None
    target_weight: float | None = Field(default=None, ge=0)
    experience: str | None = None
    days_per_week: int | None = Field(default=None, ge=1, le=7)
    preferred_days: list[int] | None = None
    typical_duration_minutes: int | None = Field(default=None, ge=10, le=240)
    available_locations: list[str] | None = None
    available_equipment: list[str] | None = None
    limitations: str | None = None
    weight_unit: str | None = None
    length_unit: str | None = None
    checkin_weekday: int | None = Field(default=None, ge=0, le=6)
    onboarding_completed: bool | None = None
    timezone: str | None = None


class ProfileOut(ORMModel):
    user: UserOut
    date_of_birth: date | None
    sex: str | None
    height: float | None
    primary_goal: str | None
    target_weight: float | None
    experience: str | None
    days_per_week: int | None
    preferred_days: list[Any]
    typical_duration_minutes: int | None
    available_locations: list[Any]
    available_equipment: list[Any]
    limitations: str | None
    weight_unit: str
    length_unit: str
    checkin_weekday: int
    onboarding_completed: bool
    timezone: str | None
