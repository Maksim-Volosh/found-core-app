from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.mappers.direction import (
    map_direction_entity_to_schema,
    map_user_direction_access_entity_to_schema,
)
from app.api.v1.schemas import DirectionResponse, UserDirectionAccessResponse
from app.api.v1.schemas.direction import UserDirectionAccessRequest
from app.core.composition.container import Container
from app.core.composition.di import get_container
from app.domain.exceptions import (
    DirectionNotFound,
    UserDirectionAccessAlreadyExists,
    UserDirectionAccessNotFound,
    UserNotFoundByUserId,
)
from app.domain.exceptions.direction import (
    DirectionNotFound,
    DirectionsNotFound,
    UserDirectionAccessNotFound,
)

router = APIRouter(prefix="/direction", tags=["Direction"])


@router.get("/")
async def get_directions(
    container: Container = Depends(get_container),
) -> List[DirectionResponse]:
    try:
        directions_response = await container.get_direction_use_case().get_directions()
        return [
            map_direction_entity_to_schema(direction)
            for direction in directions_response
        ]
    except DirectionsNotFound as e:
        raise HTTPException(status_code=404, detail=e.message)


@router.get("/{telegram_chat_id}")
async def get_direction(
    telegram_chat_id: int,
    container: Container = Depends(get_container),
) -> DirectionResponse:
    try:
        directions_response = await container.get_direction_use_case().get_direction(
            telegram_chat_id=telegram_chat_id
        )
        return map_direction_entity_to_schema(directions_response)
    except DirectionNotFound as e:
        raise HTTPException(status_code=404, detail=e.message)


@router.get("/{user_id}/access")
async def get_user_direction_access(
    user_id: int,
    telegram_chat_id: int,
    container: Container = Depends(get_container),
) -> UserDirectionAccessResponse:
    try:
        directions_response = (
            await container.get_direction_use_case().get_user_direction_access(
                user_id, telegram_chat_id
            )
        )
        return map_user_direction_access_entity_to_schema(directions_response)
    except UserDirectionAccessNotFound as e:
        raise HTTPException(status_code=404, detail=e.message)


@router.post("/access", status_code=201)
async def create_user_direction_access(
    data: UserDirectionAccessRequest,
    container: Container = Depends(get_container),
) -> UserDirectionAccessResponse:
    try:
        direction_response = await container.get_create_direction_use_case().create_user_direction_access(
            user_id=data.user_id, telegram_chat_id=data.telegram_chat_id
        )
        return map_user_direction_access_entity_to_schema(direction_response)
    except UserNotFoundByUserId as e:
        raise HTTPException(status_code=404, detail=e.message)
    except DirectionNotFound as e:
        raise HTTPException(status_code=404, detail=e.message)
    except UserDirectionAccessAlreadyExists as e:
        raise HTTPException(status_code=409, detail=e.message)
