from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import NewUserEntity, UserEntity
from app.domain.interfaces import IUserRepository
from app.infrastructure.mappers.user_mapper import (
    apply_user_entity_to_user_model,
    map_new_user_entity_to_user_model,
    map_user_model_to_user_entity,
)
from app.infrastructure.models import UserModel


class SqlAlchemyUserRepository(IUserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_telegram_id(self, telegram_id: int) -> UserEntity | None:
        result = await self._session.execute(
            select(UserModel).where(UserModel.telegram_id == telegram_id)
        )
        model = result.scalar_one_or_none()
        return map_user_model_to_user_entity(model) if model else None

    async def create(self, user: NewUserEntity) -> UserEntity:
        model = map_new_user_entity_to_user_model(user)
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return map_user_model_to_user_entity(model)

    async def update(self, user: UserEntity) -> UserEntity:
        result = await self._session.execute(select(UserModel).where(UserModel.id == user.id))
        model = result.scalar_one()
        apply_user_entity_to_user_model(user, model)
        await self._session.commit()
        await self._session.refresh(model)
        return map_user_model_to_user_entity(model)
