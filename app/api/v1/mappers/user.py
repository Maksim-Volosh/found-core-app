from app.api.v1.schemas.auth import (AuthUserRequest, UserAuthResponse,
                                     UserAuthSubscriptionResponse)
from app.domain.entities import NewUserEntity
from app.domain.entities.auth_user import AuthUserEntity


def map_user_schema_to_entity(user_request: AuthUserRequest) -> NewUserEntity:
    """Maps AuthUserRequest to NewUserEntity."""
    
    return NewUserEntity(
        telegram_id=user_request.telegram_id,
        username=user_request.username,
        first_name=user_request.first_name,
        last_name=user_request.last_name
    )
    
def map_user_entity_to_schema(user_entity: AuthUserEntity) -> UserAuthResponse:
    """Maps AuthUserEntity to UserAuthResponse."""
    
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
        
        subscription=subscription_data
    )