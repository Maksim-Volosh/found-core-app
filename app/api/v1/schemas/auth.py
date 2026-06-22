from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.domain.entities.subscription import SubscriptionStatus


class UserAuthSubscriptionResponse(BaseModel):
    expires_at: datetime
    status: SubscriptionStatus


class UserAuthResponse(BaseModel):
    user_id: int
    telegram_id: int
    username: Optional[str]
    first_name: str
    last_name: Optional[str]
    level: int
    is_banned: bool
    is_admin: bool

    subscription: Optional[UserAuthSubscriptionResponse] = None