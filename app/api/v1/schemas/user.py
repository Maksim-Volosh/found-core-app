from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.domain.entities.subscription import SubscriptionStatus


class UserSubscriptionResponse(BaseModel):
    started_at: datetime
    expires_at: datetime
    status: SubscriptionStatus


class UserWithSubscriptionResponse(BaseModel):
    user_id: int
    telegram_id: int
    username: Optional[str]
    first_name: str
    last_name: Optional[str]
    level: int
    is_banned: bool
    is_admin: bool
    is_superadmin: bool

    subscription: Optional[UserSubscriptionResponse] = None


class UserResponse(BaseModel):
    user_id: int
    telegram_id: int
    username: Optional[str]
    first_name: str
    last_name: Optional[str]
    level: int
    is_banned: bool
    is_admin: bool
    is_superadmin: bool
