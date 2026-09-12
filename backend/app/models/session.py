from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.lib.time import utcnow


class WorkoutSession(Base):
    __tablename__ = "workout_sessions"
    __table_args__ = (Index("ix_session_user_date", "user_id", "scheduled_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    template_id: Mapped[int | None] = mapped_column(
        ForeignKey("workout_templates.id", ondelete="SET NULL"), nullable=True
    )
    program_id: Mapped[int | None] = mapped_column(ForeignKey("programs.id", ondelete="SET NULL"), nullable=True)
    name: Mapped[str] = mapped_column(String(200))
    scheduled_date: Mapped[date] = mapped_column(Date, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="in_progress", index=True)
    source: Mapped[str] = mapped_column(String(32), default="scheduled")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user = relationship("User")
    template = relationship("WorkoutTemplate")
    program = relationship("Program")
    exercises = relationship(
        "PerformedExercise",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="PerformedExercise.position",
    )


class PerformedExercise(Base):
    __tablename__ = "performed_exercises"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("workout_sessions.id", ondelete="CASCADE"), index=True)
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"), index=True)
    original_exercise_id: Mapped[int | None] = mapped_column(ForeignKey("exercises.id"), nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    skipped: Mapped[bool] = mapped_column(Boolean, default=False)

    session = relationship("WorkoutSession", back_populates="exercises")
    exercise = relationship("Exercise", foreign_keys=[exercise_id])
    sets = relationship(
        "PerformedSet",
        back_populates="performed_exercise",
        cascade="all, delete-orphan",
        order_by="PerformedSet.set_number",
    )
    cardio = relationship(
        "CardioPerformance",
        back_populates="performed_exercise",
        uselist=False,
        cascade="all, delete-orphan",
    )


class PerformedSet(Base):
    __tablename__ = "performed_sets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    performed_exercise_id: Mapped[int] = mapped_column(
        ForeignKey("performed_exercises.id", ondelete="CASCADE"), index=True
    )
    set_number: Mapped[int] = mapped_column(Integer)
    set_type: Mapped[str] = mapped_column(String(32), default="working")
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    reps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rpe: Mapped[float | None] = mapped_column(Float, nullable=True)
    added_weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    assisted_weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    skipped: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rest_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_reps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    min_reps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_reps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_effort: Mapped[str | None] = mapped_column(String(32), nullable=True)
    target_rpe: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)

    performed_exercise = relationship("PerformedExercise", back_populates="sets")


class CardioPerformance(Base):
    __tablename__ = "cardio_performances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    performed_exercise_id: Mapped[int] = mapped_column(
        ForeignKey("performed_exercises.id", ondelete="CASCADE"), unique=True
    )
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    distance_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    calories: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_hr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resistance: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rpe: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    target_duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_distance_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_effort: Mapped[str | None] = mapped_column(String(32), nullable=True)

    performed_exercise = relationship("PerformedExercise", back_populates="cardio")
