from abc import ABC, abstractmethod

from app.domain.entities import SubscriptionEntity


class ISubscriptionRepository(ABC):
    @abstractmethod
    async def commit(self) -> None:
        raise NotImplementedError
    
    @abstractmethod
    async def get_subscription(self, user_id: int) -> SubscriptionEntity | None:
        raise NotImplementedError
    
    @abstractmethod
    async def create_subscription(self, subscription: SubscriptionEntity) -> None:
        raise NotImplementedError
