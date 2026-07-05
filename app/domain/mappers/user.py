from app.domain.entities import SubscriptionEntity, UserEntity, UserSubscriptionEntity


def map_to_user_subscription(
    user: UserEntity, subscription: SubscriptionEntity | None
) -> UserSubscriptionEntity:
    return UserSubscriptionEntity(user=user, subscription=subscription)
