from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    userId: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    refreshToken: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)

    expiresAt: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    ipAddress: Mapped[str | None] = mapped_column(String(45), nullable=True)

    userAgent: Mapped[str | None] = mapped_column(String(500), nullable=True)

    createdAt: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    updatedAt: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    __table_args__ = (Index("ix_sessions_user_id_expires_at", "userId", "expiresAt"),)
