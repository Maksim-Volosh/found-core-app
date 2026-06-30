from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.mappers.direction import (
    map_direction_entity_to_schema, map_direction_schema_and_id_to_entity,
    map_direction_schema_to_entity, map_user_direction_access_entity_to_schema,
    map_user_direction_access_schema_to_entity)
from app.api.v1.mappers.user import map_user_entity_to_user_schema
from app.api.v1.schemas import (ChangeUserDirectionAccessRequest,
                                CreateDirectionRequest, DirectionResponse,
                                UpdateDirectionRequest,
                                UserDirectionAccessResponse, UserResponse)
from app.api.v1.schemas.direction import UserDirectionAccessRequest
from app.core.composition.container import Container
from app.core.composition.di import get_container
from app.domain.exceptions import (DirectionAlreadyExists, DirectionNotFound,
                                   UserDirectionAccessAlreadyExists,
                                   UserDirectionAccessNotFound,
                                   UserNotFoundByUserId, UsersNotFound)

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/user")
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
    
@router.patch("/direction/access")
async def change_user_direction_access(
    user_id: int,
    telegram_chat_id: int,
    user_direction_access: ChangeUserDirectionAccessRequest,
    container: Container = Depends(get_container),
) -> UserDirectionAccessResponse:
    try:
        user_direction_access_entity = map_user_direction_access_schema_to_entity(user_id, telegram_chat_id, user_direction_access)
        response = await container.get_direction_use_case().change_user_direction_access(user_direction_access_entity)
        return map_user_direction_access_entity_to_schema(response)
    except UserDirectionAccessNotFound as e:
        raise HTTPException(status_code=404, detail=e.message)
    
@router.post("/direction", status_code=201)
async def create_direction(
    direction: CreateDirectionRequest,
    container: Container = Depends(get_container),
) -> DirectionResponse:
    try:
        direction_entity = map_direction_schema_to_entity(direction)
        direction_response = await container.get_direction_use_case().create_direction(direction_entity)
        return map_direction_entity_to_schema(direction_response)
    except DirectionAlreadyExists as e:
        raise HTTPException(status_code=409, detail=e.message)
    
@router.patch("/direction/{telegram_chat_id}")
async def change_direction(
    telegram_chat_id: int,
    direction: UpdateDirectionRequest,
    container: Container = Depends(get_container),
) -> DirectionResponse:
    try:
        direction_entity = map_direction_schema_and_id_to_entity(direction, telegram_chat_id)
        direction_response = await container.get_direction_use_case().change_direction(direction_entity)
        return map_direction_entity_to_schema(direction_response)
    except DirectionNotFound as e:
        raise HTTPException(status_code=404, detail=e.message)
    
