from app.domain.entities import AuthUserEntity, SubscriptionEntity, UserEntity


def map_to_auth_user(user: UserEntity, subscription: SubscriptionEntity | None) -> AuthUserEntity:
    return AuthUserEntity(
        user=user,
        subscription=subscription
    )