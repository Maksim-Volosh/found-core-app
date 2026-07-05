from datetime import datetime
from enum import Enum

from sqlalchemy import BigInteger, Boolean, Column, Column, DateTime
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.entities.subscription import SubscriptionStatus

from .base import Base


class Subscription(Base):
    __tablename__ = "subscription"

    subscription_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("user.user_id", ondelete="CASCADE"),
        nullable=False,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
    )

    status: Mapped[SubscriptionStatus] = mapped_column(
        SQLAlchemyEnum(SubscriptionStatus)
    )

    reminded_7_days: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    reminded_3_days: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="subscriptions")  # type: ignore
