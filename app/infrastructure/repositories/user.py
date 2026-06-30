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
    
    async def get_users(self) -> list[UserEntity] | None:
        q = await self.session.execute(select(User).order_by(User.is_admin.desc(), User.level.desc(), User.is_banned.asc()))
        user_models = q.scalars().all()
        if user_models is None:
            return None
        return [UserMapper.to_entity(user_model) for user_model in user_models]
    
    async def create_user(self, user: NewUserEntity) -> UserEntity:
        new_user = NewUserMapper.to_model(user)
        self.session.add(new_user)
        await self.session.commit()
        return UserMapper.to_entity(new_user)
    
    async def update_user(self, user: UserEntity) -> None:
        user_model = UserMapper.to_model(user)
        await self.session.merge(user_model)
        await self.session.commit()
        
    async def change_user_level(self, user_id: int, level: int) -> UserEntity | None:
        user_model = await self.session.get(User, user_id)
        if user_model is None:
            return None
        user_model.level = level
        await self.session.commit()
        return UserMapper.to_entity(user_model)
    
    async def ban_user(self, user_id: int, decision: bool) -> UserEntity | None:
        user_model = await self.session.get(User, user_id)
        if user_model is None:
            return None
        user_model.is_banned = decision
        await self.session.commit()
        return UserMapper.to_entity(user_model)