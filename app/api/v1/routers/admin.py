from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.mappers.user import map_user_entity_to_user_schema
from app.api.v1.schemas import UserResponse
from app.core.composition.container import Container
from app.core.composition.di import get_container
from app.domain.exceptions import UserNotFoundByUserId, UsersNotFound

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/users")
async def get_users(
    container: Container = Depends(get_container),
) -> list[UserResponse]:
    try:
        users = await container.get_admin_use_case().get_users()
        return [map_user_entity_to_user_schema(user) for user in users]
    except UsersNotFound as e:
        raise HTTPException(status_code=404, detail=e.message)

@router.patch("/user/{user_id}/level")
async def change_user_level(
    user_id: int,
    level: int,
    container: Container = Depends(get_container),
) -> UserResponse:
    try:
        user = await container.get_admin_use_case().change_user_level(user_id, level)
        return map_user_entity_to_user_schema(user)
    except UserNotFoundByUserId as e:
        raise HTTPException(status_code=404, detail=e.message)


@router.patch("/user/{user_id}/ban")
async def ban_user(
    user_id: int,
    decision: bool,
    container: Container = Depends(get_container),
) -> UserResponse:
    try:
        user = await container.get_admin_use_case().ban_user(user_id, decision)
        return map_user_entity_to_user_schema(user)
    except UserNotFoundByUserId as e:
        raise HTTPException(status_code=404, detail=e.message)
    
