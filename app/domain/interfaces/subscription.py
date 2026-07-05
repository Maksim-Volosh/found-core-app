from abc import ABC, abstractmethod
from datetime import datetime

from app.domain.entities import SubscriptionEntity
from app.domain.entities.subscription import SubscriptionStatus


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

    @abstractmethod
    async def update_status(
        self, subscription_id: int, status: SubscriptionStatus
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def update_subscription(
        self, subscription: SubscriptionEntity
    ) -> SubscriptionEntity | None:
        raise NotImplementedError

    @abstractmethod
    async def get_expired_subscriptions(
        self, now: datetime
    ) -> list[SubscriptionEntity]:
        raise NotImplementedError

    @abstractmethod
    async def get_subs_for_7_days_reminder(
        self, target_date: datetime
    ) -> list[SubscriptionEntity]:
        raise NotImplementedError

    @abstractmethod
    async def get_subs_for_3_days_reminder(
        self, target_date: datetime
    ) -> list[SubscriptionEntity]:
        raise NotImplementedError
