from app.domain.entities import NewPaymentEntity
from app.domain.entities.payment import PaymentEntity
from app.domain.entities.payment import PaymentEntity
from app.infrastructure.models import Payment as PaymentModel


class NewPaymentMapper:
    @staticmethod
    def to_model(entity: NewPaymentEntity) -> PaymentModel:
        return PaymentModel(
            user_id=entity.user_id,
            months=entity.months,
            amount=entity.amount,
            currency=entity.currency,
            status=entity.status,
            provider=entity.provider,
            provider_payment_id=entity.provider_payment_id,
            provider_checkout_url=entity.provider_checkout_url,
        )

    @staticmethod
    def from_model(model: PaymentModel) -> NewPaymentEntity:
        return NewPaymentEntity(
            user_id=model.user_id,
            months=model.months,
            amount=model.amount,
            currency=model.currency,
            status=model.status,
            provider=model.provider,
            provider_payment_id=model.provider_payment_id,
            provider_checkout_url=model.provider_checkout_url,
        )


class PaymentMapper:
    @staticmethod
    def to_model(entity: PaymentEntity) -> PaymentModel:
        return PaymentModel(
            payment_id=entity.payment_id,
            user_id=entity.user_id,
            amount=entity.amount,
            months=entity.months,
            currency=entity.currency,
            status=entity.status,
            provider=entity.provider,
            provider_payment_id=entity.provider_payment_id,
            provider_checkout_url=entity.provider_checkout_url,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    @staticmethod
    def from_model(model: PaymentModel) -> PaymentEntity:
        return PaymentEntity(
            payment_id=model.payment_id,
            user_id=model.user_id,
            amount=model.amount,
            months=model.months,
            currency=model.currency,
            status=model.status,
            provider=model.provider,
            provider_payment_id=model.provider_payment_id,
            provider_checkout_url=model.provider_checkout_url,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
