from app.domain.entities import NewPaymentEntity
from app.infrastructure.models import Payment as PaymentModel


class NewPaymentMapper:
    @staticmethod
    def to_model(entity: NewPaymentEntity) -> PaymentModel:
        return PaymentModel(
            user_id=entity.user_id,
            amount=entity.amount,
            currency=entity.currency,
            status=entity.status,
            provider=entity.provider,
            provider_payment_id=entity.provider_payment_id,
        )

    @staticmethod
    def from_model(model: PaymentModel) -> NewPaymentEntity:
        return NewPaymentEntity(
            user_id=model.user_id,
            amount=model.amount,
            currency=model.currency,
            status=model.status,
            provider=model.provider,
            provider_payment_id=model.provider_payment_id,
        )