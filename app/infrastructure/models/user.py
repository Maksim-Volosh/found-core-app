from datetime import datetime
from typing import List, Optional

from sqlalchemy import BigInteger, DateTime, String, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class User(Base):
    __tablename__ = "user"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True, unique=True)
    
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str] = mapped_column(String(128))
    last_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    
    level: Mapped[int] = mapped_column(Integer, default=1)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now() 
    )
        
    is_banned: Mapped[bool] = mapped_column(default=False)
    is_admin: Mapped[bool] = mapped_column(default=False)
    is_superadmin: Mapped[bool] = mapped_column(default=False)
    
    subscriptions: Mapped[List["Subscription"]] = relationship( # type: ignore
        "Subscription", 
        back_populates="user",
        cascade="all, delete-orphan"
    )
    payments: Mapped[list["Payment"]] = relationship( # type: ignore
        "Payment", 
        back_populates="user",
        cascade="all, delete-orphan"
    )
    direction_access: Mapped[List["UserDirectionAccess"]] = relationship( # type: ignore
        "UserDirectionAccess", 
        back_populates="user",
        cascade="all, delete-orphan"
    )