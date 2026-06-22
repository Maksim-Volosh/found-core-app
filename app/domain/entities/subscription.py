from datetime import datetime
from enum import Enum 
from dataclasses import dataclass
from typing import Optional

class SubscriptionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


@dataclass
class SubscriptionEntity:
    subscription_id: int
    user_id: int
    started_at: Optional[datetime]
    expires_at: datetime
    status: SubscriptionStatus