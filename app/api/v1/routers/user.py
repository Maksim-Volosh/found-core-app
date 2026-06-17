from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.schemas.user import UserRequest, UserResponse
from app.core.composition.container import Container
from app.core.composition.di import get_container
from app.domain.exceptions import UserNotFoundByTelegramId

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/users/auth")
async def auth_user(
    user: UserRequest,
    container: Container = Depends(get_container),
) -> UserResponse:
    """
    Authenticate a user by their Telegram ID.

    Args:
        user (UserRequest): The user request containing the Telegram ID.
        container (Container): The dependency injection container.

    Returns:
        UserResponse: The authenticated user's information.

    Raises:
        HTTPException: If the user is not found.
    """
    try:
        user_entity = await container.user_use_case().get_by_telegram_id(user.telegram_id)
        return UserResponse.model_validate(user_entity, from_attributes=True)
    except UserNotFoundByTelegramId as e:
        raise HTTPException(status_code=404, detail=e.message)
