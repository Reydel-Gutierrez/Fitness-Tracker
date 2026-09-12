from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.lib.time import utcnow


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    sex: Mapped[str | None] = mapped_column(String(32), nullable=True)
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    primary_goal: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    experience: Mapped[str | None] = mapped_column(String(32), nullable=True)
    days_per_week: Mapped[int | None] = mapped_column(Integer, nullable=True)
    preferred_days: Mapped[list] = mapped_column(JSON, default=list)
    typical_duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    available_locations: Mapped[list] = mapped_column(JSON, default=list)
    available_equipment: Mapped[list] = mapped_column(JSON, default=list)
    limitations: Mapped[str | None] = mapped_column(Text, nullable=True)
    weight_unit: Mapped[str] = mapped_column(String(8), default="lb")
    length_unit: Mapped[str] = mapped_column(String(8), default="in")
    checkin_weekday: Mapped[int] = mapped_column(Integer, default=4)  # Friday
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user = relationship("User", back_populates="profile")
