from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.mappers.direction import (
    map_direction_entity_to_schema, map_user_direction_access_entity_to_schema)
from app.api.v1.schemas import DirectionResponse, UserDirectionAccessResponse
from app.core.composition.container import Container
from app.core.composition.di import get_container
from app.domain.exceptions.direction import (DirectionsNotFound,
                                             UserDirectionAccessNotFound)

router = APIRouter(prefix="/direction", tags=["Direction"])

    
@router.get("/")
async def get_directions(
    container: Container = Depends(get_container),
) -> List[DirectionResponse]:
    try:
        directions_response = await container.get_direction_use_case().get_directions()
        return [map_direction_entity_to_schema(direction) for direction in directions_response]
    except DirectionsNotFound as e:
        raise HTTPException(status_code=404, detail=e.message)
    
@router.get("/access/{user_id}")
async def get_user_direction_access(
    user_id: int,
    telegram_chat_id: int,
    container: Container = Depends(get_container),
) -> UserDirectionAccessResponse:
    try:
        directions_response = await container.get_direction_use_case().get_user_direction_access(user_id, telegram_chat_id)
        return map_user_direction_access_entity_to_schema(directions_response)
    except UserDirectionAccessNotFound as e:
        raise HTTPException(status_code=404, detail=e.message)