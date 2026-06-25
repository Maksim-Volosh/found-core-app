from datetime import datetime, timedelta, timezone

import stripe

from app.domain.entities import (NewPaymentEntity, PaymentEntity,
                                 PaymentSessionEntity, SubscriptionEntity)
from app.domain.entities.payment import PaymentStatus
from app.domain.entities.subscription import SubscriptionStatus
from app.domain.exceptions import NoPaymentRequired, UserNotFoundByUserId
from app.domain.interfaces import (IPaymentProvider, IPaymentRepository,
                                   ISubscriptionRepository, IUserRepository)


class CreatePaymentUseCase:
    def __init__(
        self,
        payment_provider: IPaymentProvider,
        user_repo: IUserRepository,
        payment_repo: IPaymentRepository,
        subscription_repo: ISubscriptionRepository,
        default_currency: str,
        price_matrix: dict[int, int],
    ):
        self.payment_provider = payment_provider
        self.user_repo = user_repo
        self.payment_repo = payment_repo
        self.subscription_repo = subscription_repo
        self.default_currency = default_currency
        self.price_matrix = price_matrix

    async def execute(self, user_id: int) -> str:
        user = await self.user_repo.get_by_user_id(user_id)
        if user is None:
            raise UserNotFoundByUserId()
        price_in_cents = user.calculate_subscription_price(self.price_matrix)
        if price_in_cents == 0:
            raise NoPaymentRequired()
        subscription: SubscriptionEntity | None = await self.subscription_repo.get_subscription(user.user_id)
        if subscription is not None:
            if subscription.status == SubscriptionStatus.ACTIVE:
                raise NoPaymentRequired()
        
        active_pending_payment: PaymentEntity | None = await self.payment_repo.get_pending_payment(user.user_id)
        if active_pending_payment:
            if active_pending_payment.provider == self.payment_provider.provider:
                return active_pending_payment.provider_checkout_url
            else:
                await self.payment_repo.update_status(active_pending_payment.payment_id, PaymentStatus.CANCELLED)
        
        session_entity: PaymentSessionEntity = await self.payment_provider.create_checkout_session(
            user_id=user.user_id,
            price_in_cents=price_in_cents,
            currency=self.default_currency
        )
        
        new_payment = NewPaymentEntity(
            user_id=user.user_id,
            amount=price_in_cents,
            currency=self.default_currency,
            status=PaymentStatus.PENDING,
            provider=session_entity.provider,
            provider_payment_id=session_entity.provider_payment_id,
            provider_checkout_url=session_entity.checkout_url
        )
        
        
        await self.payment_repo.create_payment(new_payment)
        await self.payment_repo.commit()
        
        return session_entity.checkout_url
    
    
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