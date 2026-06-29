from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.mappers.direction import DirectionMapper, UserDirectionAccessMapper
from app.domain.entities import (DirectionEntity, SubscriptionEntity,
                                 UserDirectionAccessEntity)
from app.domain.interfaces import IDirectionRepository
from app.infrastructure.models import Direction, UserDirectionAccess


class SQLAlchemyDirectionRepository(IDirectionRepository):
    def __init__(self, session):
        self.session: AsyncSession = session
    
    async def create_direction(self, direction: DirectionEntity) -> DirectionEntity | None:
        direction_model = await self.session.get(Direction, direction.telegram_chat_id)
        if direction_model is not None:
            return None
        
        direction_model = DirectionMapper.to_model(direction)
        self.session.add(direction_model)
        await self.session.commit()
        return direction
    
    async def get_directions(self) -> list[DirectionEntity] | None:
        q = select(Direction)
        direction_models = await self.session.scalars(q)
        if direction_models is None:
            return None
        return [DirectionMapper.from_model(direction_model) for direction_model in direction_models]
    
    async def get_direction(self, telegram_chat_id: int) -> DirectionEntity | None:
        direction_model = await self.session.get(Direction, telegram_chat_id)
        if direction_model is None:
            return None
        await self.session.commit()
        return DirectionMapper.from_model(direction_model)
    
    async def create_user_direction_access(self, user_id: int, telegram_chat_id: int) -> UserDirectionAccessEntity | None:
        q = select(UserDirectionAccess).where(
            UserDirectionAccess.user_id == user_id,
            UserDirectionAccess.telegram_chat_id == telegram_chat_id
        )
        user_direction_access_model = await self.session.scalar(q)
        if user_direction_access_model is not None:
            return None
        
        user_direction_access_model = UserDirectionAccess(
            user_id=user_id,
            telegram_chat_id=telegram_chat_id,
        )
        self.session.add(user_direction_access_model)
        await self.session.commit()
        return UserDirectionAccessMapper.from_model(user_direction_access_model)
     
    async def change_user_direction_access(self, user_direction_access: UserDirectionAccessEntity) -> UserDirectionAccessEntity | None:
        q = select(UserDirectionAccess).where(
            UserDirectionAccess.user_id == user_direction_access.user_id,
            UserDirectionAccess.telegram_chat_id == user_direction_access.telegram_chat_id
        )
        user_direction_access_model = await self.session.scalar(q)
        if user_direction_access_model is None:
            return None
        user_direction_access_model.screening_status = user_direction_access.screening_status
        await self.session.commit()
        return UserDirectionAccessMapper.from_model(user_direction_access_model)
     
    async def change_direction(self, direction: DirectionEntity) -> DirectionEntity | None:
        direction_model = await self.session.get(Direction, direction.telegram_chat_id)
        if direction_model is None:
            return None
        direction_model.name = direction.name
        direction_model.owner_username = direction.owner_username
        direction_model.requires_screening = direction.requires_screening
        await self.session.commit()
        return DirectionMapper.from_model(direction_model)
    
    async def get_user_direction_access(self, user_id: int, telegram_chat_id: int) -> UserDirectionAccessEntity | None:
        q = select(UserDirectionAccess).where(
            UserDirectionAccess.user_id == user_id,
            UserDirectionAccess.telegram_chat_id == telegram_chat_id
        )
        user_direction_access_model = await self.session.scalar(q)
        if user_direction_access_model is None:
            return None
        return UserDirectionAccessMapper.from_model(user_direction_access_model)