from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.lib.time import utcnow


class WorkoutTemplate(Base):
    __tablename__ = "workout_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_from: Mapped[str] = mapped_column(String(32), default="manual")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user = relationship("User")
    exercises = relationship(
        "WorkoutTemplateExercise",
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="WorkoutTemplateExercise.position",
    )


class WorkoutTemplateExercise(Base):
    __tablename__ = "workout_template_exercises"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("workout_templates.id", ondelete="CASCADE"), index=True)
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"), index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    rest_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    template = relationship("WorkoutTemplate", back_populates="exercises")
    exercise = relationship("Exercise")
    sets = relationship(
        "PrescribedSet",
        back_populates="template_exercise",
        cascade="all, delete-orphan",
        order_by="PrescribedSet.set_number",
    )


class PrescribedSet(Base):
    __tablename__ = "prescribed_sets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    template_exercise_id: Mapped[int] = mapped_column(
        ForeignKey("workout_template_exercises.id", ondelete="CASCADE"), index=True
    )
    set_number: Mapped[int] = mapped_column(Integer)
    set_type: Mapped[str] = mapped_column(String(32), default="working")
    target_reps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    min_reps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_reps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_effort: Mapped[str | None] = mapped_column(String(32), nullable=True)
    target_rpe: Mapped[float | None] = mapped_column(Float, nullable=True)
    rest_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_distance_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    template_exercise = relationship("WorkoutTemplateExercise", back_populates="sets")
