from app.domain.entities.payment import NewPaymentEntity, PaymentEntity, PaymentSessionEntity, PaymentStatus
from app.domain.exceptions import NoPaymentRequired, UserNotFoundByUserId
from app.domain.interfaces import (IPaymentProvider, IPaymentRepository,
                                   IUserRepository)


class CreatePaymentUseCase:
    def __init__(
        self,
        payment_provider: IPaymentProvider,
        user_repo: IUserRepository,
        payment_repo: IPaymentRepository,
        default_currency: str,
        price_matrix: dict[int, int],
    ):
        self.payment_provider = payment_provider
        self.user_repo = user_repo
        self.payment_repo = payment_repo
        self.default_currency = default_currency
        self.price_matrix = price_matrix

    async def execute(self, user_id: int) -> str:
        user = await self.user_repo.get_by_user_id(user_id)
        if user is None:
            raise UserNotFoundByUserId()
        price_in_cents = user.calculate_subscription_price(self.price_matrix)
        if price_in_cents == 0:
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
        
        return session_entity.checkout_url