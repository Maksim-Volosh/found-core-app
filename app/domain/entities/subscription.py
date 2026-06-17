from datetime import datetime
from enum import Enum 
from dataclasses import dataclass
from typing import Optional

class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


@dataclass
class SubscriptionEntity:
    subscription_id: int
    user_id: int
    started_at: datetime
    expires_at: Optional[datetime]
    status: SubscriptionStatus