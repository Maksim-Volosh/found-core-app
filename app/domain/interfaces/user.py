from abc import ABC, abstractmethod

from app.domain.entities import NewUserEntity, UserEntity


class IUserRepository(ABC):
    @abstractmethod
    async def get_by_telegram_id(self, telegram_id: int) -> UserEntity | None:
        raise NotImplementedError
    
    @abstractmethod
    async def get_by_user_id(self, user_id: int) -> UserEntity | None:
        raise NotImplementedError
    
    @abstractmethod
    async def get_by_username(self, username: str) -> UserEntity | None:
        raise NotImplementedError
    
    @abstractmethod
    async def get_users(self) -> list[UserEntity] | None:
        raise NotImplementedError

    @abstractmethod
    async def create_user(self, user: NewUserEntity) -> UserEntity:
        raise NotImplementedError
    
    @abstractmethod
    async def update_user(self, user: UserEntity) -> None:
        raise NotImplementedError
    
    @abstractmethod
    async def change_user_level(self, user_id: int, level: int) -> UserEntity | None:
        raise NotImplementedError
    
    @abstractmethod
    async def ban_user(self, user_id: int, decision: bool) -> UserEntity | None:
        raise NotImplementedError

