from typing import List

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
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
    
    async def create_user(self, user: NewUserEntity) -> UserEntity | None:
        new_user = NewUserMapper.to_model(user)
        self.session.add(new_user)

        try:
            await self.session.flush()
        except IntegrityError as e:
            if "unique constraint" in str(e.orig):
                await self.session.rollback()
                return None
            else:
                raise
        await self.session.commit()
        return UserMapper.to_entity(new_user)

    async def get_all(self) -> List[UserEntity] | None:
        q = select(User)
        result = await self.session.execute(q)
        user_models = result.scalars().all()

        if user_models is None:
            return None

        return [UserMapper.to_entity(user_model) for user_model in user_models]