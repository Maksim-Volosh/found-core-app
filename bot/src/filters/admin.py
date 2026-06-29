from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message, TelegramObject


class IsAdminFilter(BaseFilter):
    async def __call__(self, event: TelegramObject, is_user_admin: bool) -> bool:
        if is_user_admin:
            return True

        if isinstance(event, CallbackQuery):
            await event.answer(
                text="❌ У вас нет прав администратора для этого действия!", 
                show_alert=True
            )
        elif isinstance(event, Message):
            await event.answer(
                text="❌ Эта команда доступна только администраторам бота."
            )

        return False