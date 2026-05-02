from sqlalchemy import ForeignKey, BigInteger, String, DateTime, func, Integer
from sqlalchemy.orm import Mapped, mapped_column
from bot.db.base import Base
from datetime import datetime

class PendingInvite(Base):
    __tablename__ = "pending_invites"

    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())