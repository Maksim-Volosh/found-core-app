from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.mappers.user import (map_user_entity_to_schema,
                                     map_user_schema_to_entity)
from app.api.v1.schemas.auth import AuthUserRequest, UserAuthResponse
from app.core.composition.container import Container
from app.core.composition.di import get_container
from app.domain.entities.auth_user import AuthUserEntity
from app.domain.entities.user import NewUserEntity
from app.domain.exceptions import UserIsBanned

router = APIRouter(prefix="/users", tags=["Users"])


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
        user_response: AuthUserEntity = await container.user_auth_use_case().auth(user_entity)
        return map_user_entity_to_schema(user_response)
    except UserIsBanned as e:
        raise HTTPException(status_code=403, detail=e.message)
