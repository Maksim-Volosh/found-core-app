from abc import ABC, abstractmethod

from app.domain.entities.user import NewUserEntity, UserEntity


class IUserRepository(ABC):
    @abstractmethod
    async def get_by_telegram_id(self, telegram_id: int) -> UserEntity | None: ...

    @abstractmethod
    async def create(self, user: NewUserEntity) -> UserEntity: ...

    @abstractmethod
    async def update(self, user: UserEntity) -> UserEntity: ...
