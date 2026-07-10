import logging
from datetime import datetime, timedelta, timezone

from app.domain.entities import (NewPaymentEntity, PaymentEntity,
                                 PaymentSessionEntity)
from app.domain.entities.direction import ScreeningStatus
from app.domain.entities.payment import PaymentProviderType, PaymentStatus
from app.domain.exceptions import (InvalidPaymentMonths, NoPaymentRequired,
                                   ScreeningNotPassed, UserNotFoundByUserId)
from app.domain.interfaces import (IPaymentProvider, IPaymentRepository,
                                   ISubscriptionRepository, IUserRepository)

logger = logging.getLogger(__name__)


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

    async def execute(self, user_id: int, months: int) -> str:
        logger.info(
            "Starting payment creation for user_id=%s months=%s",
            user_id,
            months,
        )
        if months <= 0 or months > 12:
            logger.warning(
                "Invalid payment months for user_id=%s: %s",
                user_id,
                months,
            )
            raise InvalidPaymentMonths()
        user = await self.user_repo.get_by_user_id(user_id)
        if user is None:
            logger.warning("User not found by user_id=%s", user_id)
            raise UserNotFoundByUserId()
        if user.screening_status == ScreeningStatus.NOT_STARTED:
            logger.warning(
                "User has not passed screening for user_id=%s", user_id
            )
            raise ScreeningNotPassed()
        price_in_cents = user.calculate_subscription_price(self.price_matrix)
        price_in_cents *= months
        logger.debug(
            "Calculated payment amount for user_id=%s: %s cents",
            user_id,
            price_in_cents,
        )
        if price_in_cents == 0 or user.is_admin:
            logger.info(
                "No payment required for user_id=%s amount=%s is_admin=%s",
                user_id,
                price_in_cents,
                user.is_admin,
            )
            raise NoPaymentRequired()

        if months >= 3:
            logger.debug(
                "Applying discount for user_id=%s months=%s before=%s",
                user_id,
                months,
                price_in_cents,
            )
            price_in_cents = round(
                price_in_cents - (price_in_cents * 0.2)
            )  # 20% discount for 3 months or more

        payment: PaymentEntity | None = await self.payment_repo.get_pending_payment(
            user.user_id
        )
        create_new_payment = True
        if (
            payment
            and payment.provider == self.payment_provider.provider
            and payment.months == months
            and payment.amount == price_in_cents
        ):
            if payment.provider == PaymentProviderType.CRYPTO:
                if (payment.created_at + timedelta(minutes=14)) > datetime.now(
                    timezone.utc
                ):
                    create_new_payment = False
            elif payment.provider == PaymentProviderType.STRIPE:
                if (payment.created_at + timedelta(hours=12)) > datetime.now(
                    timezone.utc
                ):
                    create_new_payment = False

        if not create_new_payment and payment:
            logger.info(
                "Returning existing checkout url for user_id=%s months=%s",
                user_id,
                months,
            )
            return payment.provider_checkout_url
        elif payment:
            logger.info(
                "Canceling existing payment for user_id=%s months=%s",
                user_id,
                months,
            )
            await self.payment_repo.update_status(
                payment.payment_id, PaymentStatus.CANCELLED
            )

        session_entity: PaymentSessionEntity = (
            await self.payment_provider.create_checkout_session(
                user_id=user.user_id,
                price_in_cents=price_in_cents,
                currency=self.default_currency,
            )
        )
        logger.info(
            "Created checkout session for user_id=%s months=%s",
            user_id,
            months,
        )

        new_payment = NewPaymentEntity(
            user_id=user.user_id,
            months=months,
            amount=price_in_cents,
            currency=self.default_currency,
            status=PaymentStatus.PENDING,
            provider=session_entity.provider,
            provider_payment_id=session_entity.provider_payment_id,
            provider_checkout_url=session_entity.checkout_url,
        )

        await self.payment_repo.create_payment(new_payment)
        await self.payment_repo.commit()

        logger.info(
            "Successfully created new payment for user_id=%s months=%s",
            user_id,
            months,
        )

        return session_entity.checkout_url
