from datetime import datetime, timedelta, timezone

from app.domain.entities import SubscriptionEntity
from app.domain.entities.payment import PaymentStatus
from app.domain.entities.subscription import SubscriptionStatus
from app.domain.interfaces import IPaymentRepository, ISubscriptionRepository


class ProcessSuccessfulPaymentService:
    def __init__(
        self,
        payment_repo: IPaymentRepository,
        subscription_repo: ISubscriptionRepository,
    ):
        self.payment_repo = payment_repo
        self.subscription_repo = subscription_repo

    async def execute(self, provider_payment_id: str) -> bool:
        payment = await self.payment_repo.get_by_provider_payment_id(
            provider_payment_id
        )
        if not payment:
            return False
        if payment.status == PaymentStatus.PAID:
            return True

        await self.payment_repo.update_status(payment.payment_id, PaymentStatus.PAID)

        subscription = await self.subscription_repo.get_subscription(payment.user_id)
        if subscription and subscription.status == SubscriptionStatus.ACTIVE:
            subscription.expires_at = subscription.expires_at + timedelta(days=30)
            subscription.reminded_3_days = False
            subscription.reminded_7_days = False
            await self.subscription_repo.update_subscription(subscription)
            await self.payment_repo.commit()
            return True

        now_utc = datetime.now(timezone.utc)
        expires_at = now_utc + timedelta(days=30)
        new_subscription = SubscriptionEntity(
            subscription_id=0,
            user_id=payment.user_id,
            started_at=now_utc,
            expires_at=expires_at,
            status=SubscriptionStatus.ACTIVE,
            reminded_3_days=False,
            reminded_7_days=False,
        )
        await self.subscription_repo.create_subscription(new_subscription)

        await self.payment_repo.commit()

        return True
