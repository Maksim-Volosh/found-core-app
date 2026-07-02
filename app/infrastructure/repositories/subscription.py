from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import SubscriptionEntity
from app.domain.entities.subscription import SubscriptionStatus
from app.domain.interfaces import ISubscriptionRepository
from app.infrastructure.models import Subscription
from app.infrastructure.mappers.subscription import SubscriptionMapper


class SQLAlchemySubscriptionRepository(ISubscriptionRepository):
    def __init__(self, session):
        self.session: AsyncSession = session
    
    def commit(self):
        return self.session.commit()

    async def get_subscription(self, user_id: int) -> SubscriptionEntity | None:
        q = select(Subscription).where(
            Subscription.user_id == user_id
        ).order_by(Subscription.expires_at.desc()).limit(1)
        subscription_model = await self.session.scalar(q)
        if subscription_model is None:
            return None
        return SubscriptionMapper.from_model(subscription_model)
    
    async def create_subscription(self, subscription: SubscriptionEntity) -> None:
        subscription_model = Subscription(
            user_id=subscription.user_id,
            started_at=subscription.started_at,
            expires_at=subscription.expires_at,
            status=subscription.status,
        )
        self.session.add(subscription_model)
        
    async def update_status(self, subscription_id: int, status: SubscriptionStatus) -> None:
        subscription_model = await self.session.get(Subscription, subscription_id)
        if subscription_model is None:
            return None
        subscription_model.status = status
        
    async def update_subscription(self, subscription: SubscriptionEntity) -> SubscriptionEntity | None:
        subscription_model = await self.session.get(Subscription, subscription.subscription_id)
        if subscription_model is None:
            return None
        subscription_model.started_at = subscription.started_at
        subscription_model.expires_at = subscription.expires_at
        subscription_model.status = subscription.status
        subscription_model.reminded_7_days = subscription.reminded_7_days
        subscription_model.reminded_3_days = subscription.reminded_3_days
        return SubscriptionMapper.from_model(subscription_model)
    
    async def get_expired_subscriptions(self, now: datetime) -> list[SubscriptionEntity]:
        q = select(Subscription).where(
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.expires_at < now
        )
        return [SubscriptionMapper.from_model(subscription_model) for subscription_model in await self.session.scalars(q)]
        
    async def get_subs_for_7_days_reminder(self, target_date: datetime) -> list[SubscriptionEntity]:
        q = select(Subscription).where(
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.expires_at <= target_date,
            Subscription.reminded_7_days == False
        )
        return [SubscriptionMapper.from_model(subscription_model) for subscription_model in await self.session.scalars(q)]

    async def get_subs_for_3_days_reminder(self, target_date: datetime) -> list[SubscriptionEntity]:
        q = select(Subscription).where(
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.expires_at <= target_date,
            Subscription.reminded_3_days == False
        )
        return [SubscriptionMapper.from_model(subscription_model) for subscription_model in await self.session.scalars(q)]