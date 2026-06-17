from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.schemas.user  import UserRequest, UserResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/users/auth")
async def auth_user(
    user: UserRequest,
) -> UserResponse:
    return UserResponse(
        user_id=1,
        telegram_id=user.telegram_id,
        username="username",
        first_name="first_name",
        level=1,
        is_banned=False
    )
