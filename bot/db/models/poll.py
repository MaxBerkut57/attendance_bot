from sqlalchemy import ForeignKey, Integer, BigInteger, DateTime, func, Enum as SQLEnum, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from bot.db.base import Base
from typing import List, Optional
from datetime import datetime
from enum import Enum

class PollStatus(str, Enum):
    ACTIVE = "active"
    FINISHED = "finished"

class AttendanceStatus(str, Enum):
    PRESENT = "present"
    ABSENT = "absent"

class Poll(Base):
    __tablename__ = "polls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    schedule_id: Mapped[int] = mapped_column(Integer, ForeignKey("schedule.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    active_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[PollStatus] = mapped_column(SQLEnum(PollStatus), default=PollStatus.ACTIVE)
    report_sent: Mapped[bool] = mapped_column(Boolean, default=False)

    schedule: Mapped["Schedule"] = relationship(back_populates="polls")
    messages: Mapped[List["PollMessage"]] = relationship(back_populates="poll")
    attendances: Mapped[List["Attendance"]] = relationship(back_populates="poll")


class PollMessage(Base):
    __tablename__ = "poll_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    poll_id: Mapped[int] = mapped_column(Integer, ForeignKey("polls.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"))
    message_id: Mapped[int] = mapped_column(BigInteger)  # ID сообщения в чате пользователя
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    poll: Mapped["Poll"] = relationship(back_populates="messages")
    user: Mapped["User"] = relationship(back_populates="poll_messages")


class Attendance(Base):
    __tablename__ = "attendance"

    poll_id: Mapped[int] = mapped_column(Integer, ForeignKey("polls.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True)
    status: Mapped[AttendanceStatus] = mapped_column(SQLEnum(AttendanceStatus))
    answered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    poll: Mapped["Poll"] = relationship(back_populates="attendances")
    user: Mapped["User"] = relationship(back_populates="attendances")