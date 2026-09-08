from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )

    password: Mapped[str | None] = mapped_column(String(255), nullable=True)

    isEmailVerified: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    provider: Mapped[str] = mapped_column(String(50), default="EMAIL", nullable=False)

    providerId: Mapped[str | None] = mapped_column(String(255), nullable=True)

    role: Mapped[str] = mapped_column(String(50), default="USER", nullable=False)

    avatar: Mapped[str | None] = mapped_column(String(500), nullable=True)

    createdAt: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    updatedAt: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
