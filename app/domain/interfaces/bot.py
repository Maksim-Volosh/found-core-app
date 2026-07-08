from abc import ABC, abstractmethod


class IBotService(ABC):
    @abstractmethod
    async def close(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def send_message(self, telegram_id: int, text: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def ban_user(self, telegram_id: int, chat_id: int) -> bool:
        raise NotImplementedError
