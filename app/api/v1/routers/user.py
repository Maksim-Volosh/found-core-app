from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.mappers.user import (map_user_entity_to_user_auth_schema,
                                     map_user_with_subscription_entity_to_schema,
                                     map_user_schema_to_entity)
from app.api.v1.schemas import AuthUserRequest, UserAuthResponse, UserWithSubscriptionResponse
from app.core.composition.container import Container
from app.core.composition.di import get_container
from app.domain.entities import NewUserEntity, UserSubscriptionEntity
from app.domain.exceptions import UserIsBanned, UserNotFoundByUserId

router = APIRouter(prefix="/user", tags=["User"])


@router.post("/auth")
async def auth_user(
    user: AuthUserRequest,
    container: Container = Depends(get_container),
) -> UserAuthResponse:
    """
    Authenticate a user by their Telegram ID.

    Args:
        user (AuthUserRequest): The user request containing the Telegram ID.
        container (Container): The dependency injection container.

    Returns:
        UserAuthResponse: The authenticated user's information.
    Raises:
        HTTPException: If the user is banned.
    """
    
    try:
        user_entity: NewUserEntity = map_user_schema_to_entity(user)
        user_response: UserSubscriptionEntity = await container.get_user_auth_use_case().auth(user_entity)
        return map_user_entity_to_user_auth_schema(user_response)
    except UserIsBanned as e:
        raise HTTPException(status_code=403, detail=e.message)
    
@router.get("/{user_id}")
async def get_user_info(
    user_id: int,
    container: Container = Depends(get_container),
) -> UserWithSubscriptionResponse:
    """
    Get user information by user ID.

    Args:
        user_id (int): The ID of the user.
        container (Container): The dependency injection container.

    Returns:
        UserWithSubscriptionResponse: The user's information.
    Raises:
        HTTPException: If the user is banned or not found.
    """
    
    try:
        user_response: UserSubscriptionEntity = await container.get_user_info_use_case().get_user_info(user_id)
        return map_user_with_subscription_entity_to_schema(user_response)
    except UserIsBanned as e:
        raise HTTPException(status_code=403, detail=e.message)
    except UserNotFoundByUserId as e:
        raise HTTPException(status_code=404, detail=e.message)