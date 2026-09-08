from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class OTP(Base):
    __tablename__ = "otps"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    userId: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    code: Mapped[str] = mapped_column(String(255), nullable=False)

    expiresAt: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    createdAt: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
