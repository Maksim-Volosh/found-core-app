from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class SubscriptionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


@dataclass
class SubscriptionEntity:
    subscription_id: int
    user_id: int
    started_at: datetime
    expires_at: datetime
    status: SubscriptionStatus
    
    def is_active(self) -> bool:
        return self.status == SubscriptionStatus.ACTIVE and self.expires_at > datetime.now(timezone.utc)