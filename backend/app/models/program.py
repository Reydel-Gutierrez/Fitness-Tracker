from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.lib.time import utcnow


class Program(Base):
    __tablename__ = "programs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    generated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user = relationship("User")
    workouts = relationship(
        "ProgramWorkout",
        back_populates="program",
        cascade="all, delete-orphan",
        order_by="ProgramWorkout.position",
    )


class ProgramWorkout(Base):
    __tablename__ = "program_workouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"), index=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("workout_templates.id"), index=True)
    weekday: Mapped[int] = mapped_column(Integer)  # 0=Monday
    position: Mapped[int] = mapped_column(Integer, default=0)
    name_override: Mapped[str | None] = mapped_column(String(200), nullable=True)

    program = relationship("Program", back_populates="workouts")
    template = relationship("WorkoutTemplate")
