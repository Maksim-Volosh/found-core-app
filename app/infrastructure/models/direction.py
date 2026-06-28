from typing import List

from sqlalchemy import BigInteger, Boolean
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.entities.direction import ScreeningStatus

from .base import Base


class Direction(Base):
    __tablename__ = "direction"

    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_username: Mapped[str] = mapped_column(String(64), nullable=False)
    requires_screening: Mapped[bool] = mapped_column(Boolean, default=False)

    directions: Mapped[List["UserDirectionAccess"]] = relationship(
        "UserDirectionAccess", 
        back_populates="direction",
        cascade="all, delete-orphan"
    )


class UserDirectionAccess(Base):
    __tablename__ = "user_direction_access"

    user_direction_access_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("user.user_id", ondelete="CASCADE"))
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("direction.telegram_chat_id", ondelete="CASCADE"), index=True)
    
    screening_status: Mapped[ScreeningStatus] = mapped_column(SQLAlchemyEnum(ScreeningStatus), default=ScreeningStatus.NOT_STARTED)
    
    user: Mapped["User"] = relationship("User", back_populates="direction_access") # type: ignore
    direction: Mapped["Direction"] = relationship("Direction", back_populates="directions")