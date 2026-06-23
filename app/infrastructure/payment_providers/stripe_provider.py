from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import PaymentSessionEntity, SubscriptionEntity
from app.domain.entities.payment import PaymentProviderType
from app.domain.interfaces import IPaymentProvider
from app.infrastructure.models import Subscription


class StripePaymentProvider(IPaymentProvider):
    async def create_checkout_session(self, user_id: int, price_in_cents: int) -> PaymentSessionEntity:
        return PaymentSessionEntity(
            provider=PaymentProviderType.STRIPE,
            provider_payment_id=f"stripe_session_{user_id}_{price_in_cents}",
            checkout_url="https://example.com/checkout",
        )