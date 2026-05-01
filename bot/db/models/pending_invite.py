from sqlalchemy import ForeignKey, BigInteger, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from bot.db.base import Base
from datetime import datetime

class PendingInvite(Base):
    __tablename__ = "pending_invites"

    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())