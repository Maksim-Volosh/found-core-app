from abc import ABC, abstractmethod
from app.domain.entities import SubscriptionEntity


class ISubscriptionRepository(ABC):
    @abstractmethod
    async def get_subscription(self, user_id: int) -> SubscriptionEntity | None:
        raise NotImplementedError
