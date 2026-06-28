from app.api.v1.schemas import (ChangeUserDirectionAccessRequest,
                                CreateDirectionRequest, DirectionResponse,
                                UserDirectionAccessResponse, UpdateDirectionRequest)
from app.domain.entities import DirectionEntity, UserDirectionAccessEntity


def map_direction_schema_to_entity(direction_request: CreateDirectionRequest) -> DirectionEntity:
    """Maps CreateDirectionRequest to DirectionEntity."""
    
    return DirectionEntity(
        telegram_chat_id=direction_request.telegram_chat_id,
        name=direction_request.name,
        owner_username=direction_request.owner_username,
        requires_screening=direction_request.requires_screening
    )
    
def map_direction_schema_and_id_to_entity(direction_request: UpdateDirectionRequest, telegram_chat_id: int) -> DirectionEntity:
    """Maps UpdateDirectionRequest and telegram_chat_id to DirectionEntity."""
    
    return DirectionEntity(
        telegram_chat_id=telegram_chat_id,
        name=direction_request.name,
        owner_username=direction_request.owner_username,
        requires_screening=direction_request.requires_screening
    )

def map_direction_entity_to_schema(direction_entity: DirectionEntity) -> DirectionResponse:
    """Maps DirectionEntity to DirectionResponse."""
    
    return DirectionResponse(
        telegram_chat_id=direction_entity.telegram_chat_id,
        name=direction_entity.name,
        owner_username=direction_entity.owner_username,
        requires_screening=direction_entity.requires_screening
    )

def map_user_direction_access_schema_to_entity(user_direction_access_schema: ChangeUserDirectionAccessRequest) -> UserDirectionAccessEntity:
    """Maps ChangeUserDirectionAccessRequest to UserDirectionAccessEntity."""
    
    return UserDirectionAccessEntity(
        user_id=user_direction_access_schema.user_id,
        telegram_chat_id=user_direction_access_schema.telegram_chat_id,
        screening_status=user_direction_access_schema.screening_status
    )
    
def map_user_direction_access_entity_to_schema(user_direction_access_entity: UserDirectionAccessEntity) -> UserDirectionAccessResponse:
    """Maps UserDirectionAccessEntity to UserDirectionAccessResponse."""
    
    return UserDirectionAccessResponse(
        user_id=user_direction_access_entity.user_id,
        telegram_chat_id=user_direction_access_entity.telegram_chat_id,
        screening_status=user_direction_access_entity.screening_status
    )