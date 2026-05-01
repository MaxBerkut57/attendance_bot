from sqlalchemy import BigInteger, String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from bot.db.base import Base
from typing import List, Optional
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    full_name: Mapped[str] = mapped_column(String(255))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_curator: Mapped[bool] = mapped_column(Boolean, default=False)  # глобальный флаг куратора (опционально)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Отношения
    group_memberships: Mapped[List["GroupMembership"]] = relationship(back_populates="user")
    curated_groups: Mapped[List["GroupCurator"]] = relationship(back_populates="user")
    poll_messages: Mapped[List["PollMessage"]] = relationship(back_populates="user")
    attendances: Mapped[List["Attendance"]] = relationship(back_populates="user")