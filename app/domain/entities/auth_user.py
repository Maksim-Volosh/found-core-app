from dataclasses import dataclass
from typing import Optional

from app.domain.entities.subscription import SubscriptionEntity
from app.domain.entities import UserEntity


@dataclass
class AuthUserEntity:
    user: UserEntity
    subscription: Optional[SubscriptionEntity] = None
            