from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject


class AdminCheckMiddleware(BaseMiddleware):
    def __init__(self, super_admin: bool = False) -> None:
        self.super_admin = super_admin

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        is_admin = data.get("is_user_admin", False)
        is_superadmin = data.get("is_user_superadmin", False)
        if self.super_admin:
            if not is_superadmin:
                if isinstance(event, CallbackQuery):
                    await event.answer(
                        text="❌ У вас нет прав суперадминистратора для этого действия!",
                        show_alert=True,
                    )
                elif isinstance(event, Message):
                    await event.answer(
                        text="❌ Эта команда доступна только суперадминистраторам бота."
                    )
                return

        if not is_admin and not is_superadmin:
            if isinstance(event, CallbackQuery):
                await event.answer(
                    text="❌ У вас нет прав администратора для этого действия!",
                    show_alert=True,
                )
            elif isinstance(event, Message):
                await event.answer(
                    text="❌ Эта команда доступна только администраторам бота."
                )
            return

        return await handler(event, data)
