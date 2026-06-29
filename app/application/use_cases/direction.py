from app.domain.entities import DirectionEntity, UserDirectionAccessEntity
from app.domain.exceptions import (DirectionAlreadyExists, DirectionNotFound,
                                   DirectionsNotFound,
                                   UserDirectionAccessAlreadyExists,
                                   UserDirectionAccessNotFound)
from app.domain.interfaces import IDirectionRepository


class DirectionUseCase:
    def __init__(self, repo: IDirectionRepository) -> None:
        self.repo = repo

    async def create_direction(self, direction: DirectionEntity) -> DirectionEntity:
        direction_entity = await self.repo.create_direction(direction)
        
        if direction_entity is None:
            raise DirectionAlreadyExists()
        
        return direction_entity
    
    async def get_directions(self) -> list[DirectionEntity]:
        directions = await self.repo.get_directions()
        
        if directions is None:
            raise DirectionsNotFound()
        
        return directions
    
    async def get_direction(self, telegram_chat_id: int) -> DirectionEntity:
        direction = await self.repo.get_direction(telegram_chat_id=telegram_chat_id)
        
        if direction is None:
            raise DirectionNotFound()
        
        return direction
    
    async def get_user_direction_access(self, user_id: int, telegram_chat_id: int) -> UserDirectionAccessEntity:
        user_direction = await self.repo.get_user_direction_access(user_id, telegram_chat_id)
        
        if user_direction is None:
            raise UserDirectionAccessNotFound()
        
        return user_direction
    
    async def create_user_direction_access(self, user_id: int, telegram_chat_id: int) -> UserDirectionAccessEntity:
        user_direction = await self.repo.create_user_direction_access(user_id=user_id, telegram_chat_id=telegram_chat_id)
        
        if user_direction is None:
            raise UserDirectionAccessAlreadyExists()
        
        return user_direction
    
    async def change_user_direction_access(self, user_direction_access: UserDirectionAccessEntity) -> UserDirectionAccessEntity:
        user_direction = await self.repo.change_user_direction_access(user_direction_access)
        
        if user_direction is None:
            raise UserDirectionAccessNotFound()
        
        return user_direction
    
    async def change_direction(self, direction: DirectionEntity) -> DirectionEntity:
        user_direction = await self.repo.change_direction(direction)
        
        if user_direction is None:
            raise DirectionNotFound()
        
        return user_direction
    
        