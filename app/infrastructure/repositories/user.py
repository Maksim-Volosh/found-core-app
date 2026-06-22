from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import NewUserEntity, UserEntity
from app.domain.interfaces import IUserRepository
from app.infrastructure.mappers.user_mapper import NewUserMapper, UserMapper
from app.infrastructure.models import User


class SQLAlchemyUserRepository(IUserRepository):
    def __init__(self, session):
        self.session: AsyncSession = session

    async def get_by_telegram_id(self, telegram_id: int) -> UserEntity | None:
        q = select(User).where(
            User.telegram_id == telegram_id
        )
        user_model = await self.session.scalar(q)

        if user_model is None:
            return None
        return UserMapper.to_entity(user_model)
    
    async def get_by_user_id(self, user_id: int) -> UserEntity | None:
        user_model = await self.session.get(User, user_id)
        if user_model is None:
            return None
        return UserMapper.to_entity(user_model)
    
    async def create_user(self, user: NewUserEntity) -> UserEntity:
        new_user = NewUserMapper.to_model(user)
        self.session.add(new_user)
        await self.session.commit()
        return UserMapper.to_entity(new_user)
    
    async def update_user(self, user: UserEntity) -> None:
        user_model = UserMapper.to_model(user)
        await self.session.merge(user_model)
        await self.session.commit()