from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.domain.entities.subscription import SubscriptionStatus
    

class UserSubscriptionResponse(BaseModel):
    started_at: datetime
    expires_at: datetime
    status: SubscriptionStatus


class UserResponse(BaseModel):
    user_id: int
    level: int
    is_banned: bool
    is_admin: bool

    subscription: Optional[UserSubscriptionResponse] = None