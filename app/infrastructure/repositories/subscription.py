from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import SubscriptionEntity
from app.domain.entities.subscription import SubscriptionStatus
from app.domain.interfaces import ISubscriptionRepository
from app.infrastructure.models import Subscription


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
        return SubscriptionEntity(
            subscription_id=subscription_model.subscription_id,
            user_id=subscription_model.user_id,
            started_at=subscription_model.started_at,
            expires_at=subscription_model.expires_at,
            status=subscription_model.status,
        )
    
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
    
    async def get_expired_subscriptions(self, now: datetime) -> list[SubscriptionEntity]:
        q = select(Subscription).where(
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.expires_at < now
        )
        return [SubscriptionEntity(
            subscription_id=subscription_model.subscription_id,
            user_id=subscription_model.user_id,
            started_at=subscription_model.started_at,
            expires_at=subscription_model.expires_at,
            status=subscription_model.status,
        ) for subscription_model in await self.session.scalars(q)]