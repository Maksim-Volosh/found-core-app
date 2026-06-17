from datetime import datetime
from enum import Enum

from sqlalchemy import BigInteger, DateTime
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class SubStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class Subscription(Base):
    __tablename__ = "subscription"

    sub_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("user.user_id"),
        nullable=False,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )    
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
    )
    
    status: Mapped[SubStatus] = mapped_column(SQLAlchemyEnum(SubStatus))
    user: Mapped["User"] = relationship("User", back_populates="subscriptions") # type: ignore