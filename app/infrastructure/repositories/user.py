from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.user import NewUserEntity, UserEntity
from app.domain.interfaces.user import IUserRepository
from app.infrastructure.mappers.user_mapper import (
    apply_entity_to_model,
    map_model_to_entity,
    map_new_entity_to_model,
)
from app.infrastructure.models.user import UserModel


class SqlAlchemyUserRepository(IUserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_telegram_id(self, telegram_id: int) -> UserEntity | None:
        result = await self._session.execute(
            select(UserModel).where(UserModel.telegram_id == telegram_id)
        )
        model = result.scalar_one_or_none()
        return map_model_to_entity(model) if model else None

    async def create(self, user: NewUserEntity) -> UserEntity:
        model = map_new_entity_to_model(user)
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return map_model_to_entity(model)

    async def update(self, user: UserEntity) -> UserEntity:
        result = await self._session.execute(select(UserModel).where(UserModel.id == user.id))
        model = result.scalar_one()
        apply_entity_to_model(user, model)
        await self._session.commit()
        await self._session.refresh(model)
        return map_model_to_entity(model)
