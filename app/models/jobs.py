from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    prompt: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    originalImageUrl: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    generationType: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    settings: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="QUEUED",
        nullable=False,
        index=True,
    )

    createdAt: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
