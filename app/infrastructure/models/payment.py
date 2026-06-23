from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Text
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy import ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.entities.payment import PaymentProviderType, PaymentStatus

from .base import Base


class Payment(Base):
    __tablename__ = "payment"

    payment_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("user.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    user: Mapped["User"] = relationship("User", back_populates="payments") # type: ignore

    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    
    status: Mapped[PaymentStatus] = mapped_column(
        SQLAlchemyEnum(PaymentStatus), 
        default=PaymentStatus.PENDING,
        index=True
    )
    
    provider: Mapped[PaymentProviderType] = mapped_column(
        SQLAlchemyEnum(PaymentProviderType),
        default=PaymentProviderType.STRIPE
    )
    provider_payment_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    provider_checkout_url: Mapped[str] = mapped_column(Text, nullable=False)


    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())