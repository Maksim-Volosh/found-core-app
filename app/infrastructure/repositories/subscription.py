from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import SubscriptionEntity
from app.domain.interfaces import ISubscriptionRepository
from app.infrastructure.models import Subscription


class SQLAlchemySubscriptionRepository(ISubscriptionRepository):
    def __init__(self, session):
        self.session: AsyncSession = session

    async def get_subscription(self, user_id: int) -> SubscriptionEntity | None:
        q = select(Subscription).where(
            Subscription.user_id == user_id
        )
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