from sqlalchemy import ForeignKey, Integer, Date, Time, String, DateTime, func, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from bot.db.base import Base
from typing import List, Optional
from datetime import date, time, datetime

class Schedule(Base):
    __tablename__ = "schedule"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(Integer, ForeignKey("groups.id", ondelete="CASCADE"))
    date: Mapped[date] = mapped_column(Date)
    time_start: Mapped[time] = mapped_column(Time)
    time_end: Mapped[time] = mapped_column(Time)
    discipline: Mapped[str] = mapped_column(String(255))
    type: Mapped[str] = mapped_column(String(20))  # lecture, practice, lab, other
    teacher: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    audience: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    group: Mapped["Group"] = relationship(back_populates="schedules")
    polls: Mapped[List["Poll"]] = relationship(back_populates="schedule")