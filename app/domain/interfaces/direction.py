from abc import ABC, abstractmethod

from app.domain.entities import DirectionEntity, UserDirectionAccessEntity


class IDirectionRepository(ABC):
    @abstractmethod
    async def create_direction(
        self, direction: DirectionEntity
    ) -> DirectionEntity | None:
        raise NotImplementedError

    @abstractmethod
    async def get_directions(self) -> list[DirectionEntity] | None:
        raise NotImplementedError

    @abstractmethod
    async def get_direction(self, telegram_chat_id: int) -> DirectionEntity | None:
        raise NotImplementedError

    @abstractmethod
    async def create_user_direction_access(
        self, user_id: int, telegram_chat_id: int
    ) -> UserDirectionAccessEntity | None:
        raise NotImplementedError

    @abstractmethod
    async def change_user_direction_access(
        self, user_direction_access: UserDirectionAccessEntity
    ) -> UserDirectionAccessEntity | None:
        raise NotImplementedError

    @abstractmethod
    async def change_direction(
        self, direction: DirectionEntity
    ) -> DirectionEntity | None:
        raise NotImplementedError

    @abstractmethod
    async def get_user_direction_access(
        self, user_id: int, telegram_chat_id: int
    ) -> UserDirectionAccessEntity | None:
        raise NotImplementedError
