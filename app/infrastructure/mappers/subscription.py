from app.domain.entities import SubscriptionEntity
from app.infrastructure.models import Subscription as SubscriptionModel


class SubscriptionMapper:
    @staticmethod
    def to_model(entity: SubscriptionEntity) -> SubscriptionModel:
        return SubscriptionModel(
            subscription_id=entity.subscription_id,
            user_id=entity.user_id,
            started_at=entity.started_at,
            expires_at=entity.expires_at,
            status=entity.status,
            reminded_3_days=entity.reminded_3_days,
            reminded_7_days=entity.reminded_7_days,
        )

    @staticmethod
    def from_model(model: SubscriptionModel) -> SubscriptionEntity:
        return SubscriptionEntity(
            subscription_id=model.subscription_id,
            user_id=model.user_id,
            started_at=model.started_at,
            expires_at=model.expires_at,
            status=model.status,
            reminded_3_days=model.reminded_3_days,
            reminded_7_days=model.reminded_7_days,
        )
