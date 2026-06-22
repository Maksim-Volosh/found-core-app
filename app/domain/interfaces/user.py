from abc import ABC, abstractmethod
from typing import List

from app.domain.entities import NewUserEntity, UserEntity


class IUserRepository(ABC):
    @abstractmethod
    async def get_by_telegram_id(self, telegram_id: int) -> UserEntity | None:
        raise NotImplementedError
    
    @abstractmethod
    async def get_by_user_id(self, user_id: int) -> UserEntity | None:
        raise NotImplementedError

    @abstractmethod
    async def create_user(self, user: NewUserEntity) -> UserEntity:
        raise NotImplementedError
    
    @abstractmethod
    async def update_user(self, user: UserEntity) -> None:
        raise NotImplementedError

