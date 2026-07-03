from app.api.v1.schemas.auth import (AuthUserRequest, UserAuthResponse,
                                     UserAuthSubscriptionResponse)
from app.api.v1.schemas.user import (UserResponse, UserSubscriptionResponse,
                                     UserWithSubscriptionResponse)
from app.domain.entities import NewUserEntity, UserSubscriptionEntity
from app.domain.entities.user import UserEntity


def map_user_schema_to_entity(user_request: AuthUserRequest) -> NewUserEntity:
    """Maps AuthUserRequest to NewUserEntity."""
    
    return NewUserEntity(
        telegram_id=user_request.telegram_id,
        username=user_request.username,
        first_name=user_request.first_name,
        last_name=user_request.last_name
    )
    
def map_user_entity_to_user_auth_schema(user_entity: UserSubscriptionEntity) -> UserAuthResponse:
    """Maps UserSubscriptionEntity to UserAuthResponse."""
    
    subscription_data = None
    if user_entity.subscription:
        subscription_data = UserAuthSubscriptionResponse(
            expires_at=user_entity.subscription.expires_at,
            status=user_entity.subscription.status
        )
    
    return UserAuthResponse(
        user_id=user_entity.user.user_id,
        telegram_id=user_entity.user.telegram_id,
        username=user_entity.user.username,
        first_name=user_entity.user.first_name,
        last_name=user_entity.user.last_name,
        level=user_entity.user.level,
        is_banned=user_entity.user.is_banned,
        is_admin=user_entity.user.is_admin,
        is_superadmin=user_entity.user.is_superadmin,
        
        subscription=subscription_data
    )
    
def map_user_with_subscription_entity_to_schema(user_entity: UserSubscriptionEntity) -> UserWithSubscriptionResponse:
    """Maps UserSubscriptionEntity to UserWithSubscriptionResponse."""
    
    subscription_data = None
    if user_entity.subscription:
        subscription_data = UserSubscriptionResponse(
            started_at=user_entity.subscription.started_at,
            expires_at=user_entity.subscription.expires_at,
            status=user_entity.subscription.status,
        )
    
    return UserWithSubscriptionResponse(
        user_id=user_entity.user.user_id,
        telegram_id=user_entity.user.telegram_id,
        username=user_entity.user.username,
        first_name=user_entity.user.first_name,
        last_name=user_entity.user.last_name,
        level=user_entity.user.level,
        is_banned=user_entity.user.is_banned,
        is_admin=user_entity.user.is_admin,
        is_superadmin=user_entity.user.is_superadmin,
        
        subscription=subscription_data
    )
    
def map_user_entity_to_user_schema(user_entity: UserEntity) -> UserResponse:    
    return UserResponse(
        user_id=user_entity.user_id,
        telegram_id=user_entity.telegram_id,
        username=user_entity.username,
        first_name=user_entity.first_name,
        last_name=user_entity.last_name,
        level=user_entity.level,
        is_banned=user_entity.is_banned,
        is_admin=user_entity.is_admin,
        is_superadmin=user_entity.is_superadmin
    )