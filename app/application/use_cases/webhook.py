from datetime import datetime, timedelta, timezone

import stripe

from app.domain.entities import SubscriptionEntity
from app.domain.entities.payment import PaymentStatus
from app.domain.entities.subscription import SubscriptionStatus
from app.domain.interfaces import IPaymentRepository, ISubscriptionRepository


class ProcessSuccessfulPaymentUseCase:
    def __init__(
        self,
        payment_repo: IPaymentRepository,
        subscription_repo: ISubscriptionRepository,
        webhook_secret: str,
    ):
        self.payment_repo = payment_repo
        self.subscription_repo = subscription_repo
        self.webhook_secret = webhook_secret

    async def execute(self, payload: bytes, sig_header: str) -> bool:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, self.webhook_secret)
        except (ValueError, stripe.SignatureVerificationError):
            return False

        if event["type"] != "checkout.session.completed":
            return True

        session_obj = event["data"]["object"]
        provider_payment_id = session_obj.id
        if not provider_payment_id:
            return False

        payment = await self.payment_repo.get_by_provider_payment_id(provider_payment_id)
        if not payment:
            return False
        if payment.status == PaymentStatus.PAID:
            return True
        
        await self.payment_repo.update_status(payment.payment_id, PaymentStatus.PAID)

        now_utc = datetime.now(timezone.utc)
        expires_at = now_utc + timedelta(days=30)
        new_subscription = SubscriptionEntity(
            subscription_id=0,
            user_id=payment.user_id,
            started_at=now_utc,
            expires_at=expires_at,
            status=SubscriptionStatus.ACTIVE
        )
        await self.subscription_repo.create_subscription(new_subscription)

        await self.payment_repo.commit()
        
        return True