from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from src.container import container


class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        state = data.get("state")
        
        backend_user_id = None
        is_admin = False

        if isinstance(event, (Message, CallbackQuery)):
            user = event.from_user
            if user:
                auth_data = {
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name
                }

                try:
                    user_data = await container.auth_service.auth(auth_data, user.id)
                    
                    if user_data is None:
                        await self._send_ban_message(event)
                        return
                    
                    backend_user_id = user_data["user_id"]
                    is_admin = user_data["is_admin"]
                
                except Exception:
                    await self._send_error_message(event)
                    return

        data["backend_user_id"] = backend_user_id
        data["is_user_admin"] = is_admin

        return await handler(event, data)
    
    async def _send_ban_message(self, event: TelegramObject) -> None:
            """Вспомогательный метод для отправки уведомления о бане"""
            text = "❌ Вы были заблокированы в данном сообществе. \n\nПожалуйста, обратитесь к администратору для получения дополнительной информации."
            
            if isinstance(event, Message):
                await event.answer(text, parse_mode="Markdown")
            elif isinstance(event, CallbackQuery) and event.message:
                await event.answer()
                await event.message.answer(text, parse_mode="Markdown")
                
    async def _send_error_message(self, event: TelegramObject) -> None:
            """Вспомогательный метод на случай, если бэкенд недоступен"""
            text = "⚠️ Сервер временно недоступен. Пожалуйста, попробуйте позже."
            if isinstance(event, Message):
                await event.answer(text)
            elif isinstance(event, CallbackQuery) and event.message:
                await event.answer(text, show_alert=True)