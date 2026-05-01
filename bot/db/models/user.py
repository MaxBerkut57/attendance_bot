from sqlalchemy import BigInteger, String, Boolean, DateTime, func, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from bot.db.base import Base
from typing import List, Optional
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(BigInteger, unique=True, nullable=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    full_name: Mapped[str] = mapped_column(String(255))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_curator: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


    group_memberships: Mapped[List["GroupMembership"]] = relationship(back_populates="user")
    curated_groups: Mapped[List["GroupCurator"]] = relationship(back_populates="user")
    poll_messages: Mapped[List["PollMessage"]] = relationship(back_populates="user")
    attendances: Mapped[List["Attendance"]] = relationship(back_populates="user")