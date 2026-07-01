from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

class AdminCheckMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        is_admin = data.get("is_user_admin", False)

        if not is_admin:
            if isinstance(event, CallbackQuery):
                await event.answer(
                    text="❌ У вас нет прав администратора для этого действия!", 
                    show_alert=True
                )
            elif isinstance(event, Message):
                await event.answer(
                    text="❌ Эта команда доступна только администраторам бота."
                )
            return

        return await handler(event, data)