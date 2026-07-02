import logging
from aiogram import Bot
from app.domain.interfaces import IBotService
from app.core.config import settings 

logger = logging.getLogger(__name__)

class TelegramBotService(IBotService):
    def __init__(self):
        self.bot = Bot(token=settings.telegram.bot_token)

    async def close(self) -> None:
        if hasattr(self, "bot") and self.bot.session:
            await self.bot.session.close()

    async def send_message(self, telegram_id: int, text: str) -> bool:
        try:
            await self.bot.send_message(chat_id=telegram_id, text=text, parse_mode="HTML")
            return True
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение пользователю {telegram_id}: {e}")
            return False

    async def ban_user(self, telegram_id: int, chat_id: int) -> bool:
        try:
            await self.bot.ban_chat_member(chat_id=chat_id, user_id=telegram_id)
            return True
        except Exception as e:
            logger.error(f"Не удалось заблокировать пользователя {telegram_id} в чате {chat_id}: {e}")
            return False