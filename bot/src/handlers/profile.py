from datetime import datetime
from typing import Any

from aiogram import Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.filters.chat_member_updated import ChatMemberUpdatedFilter, JOIN_TRANSITION
from aiogram.types import ChatMemberUpdated
from src.container import container
import src.keyboards.keyboards as kb

router = Router()
router.message.filter(F.chat.type == "private")

@router.callback_query(F.data == "profile")
async def profile_handler(callback_query: CallbackQuery, backend_user_id: int) -> None:
    if not isinstance(callback_query.message, Message):
        return
    
    await callback_query.answer()
    user_data = await container.user_service.get_user_info(backend_user_id)
    
    if user_data is None:
        text = "❌ Вы были заблокированы в данном сообществе. \n\nПожалуйста, обратитесь к администратору для получения дополнительной информации."
        await callback_query.message.answer(text, parse_mode="Markdown")
        return
    
    if user_data["subscription"] is None:
        await callback_query.message.edit_text(
            f"Привет, {user_data['first_name']}! \n\nВаш уровень в сообществе: {user_data['level']}/10",
            reply_markup=kb.get_back_keyboard()
        )
        return
    
    date_string = user_data["subscription"]["expires_at"]
    dt_object = datetime.fromisoformat(date_string.replace("Z", "+00:00"))
    end_date_time = dt_object.strftime("%d %B %H:%M")
    
    start_date_string = user_data["subscription"]["started_at"]
    start_dt_object = datetime.fromisoformat(start_date_string.replace("Z", "+00:00"))
    start_date_time = start_dt_object.strftime("%d %B %H:%M")
    
    
    await callback_query.message.edit_text(
        f"Привет, {user_data['first_name']}! \n\nВаш уровень в сообществе: {user_data['level']}/10 \nДата начала подписки: {start_date_time} \nДата окончания подписки: {end_date_time}",
        reply_markup=kb.get_back_keyboard()
    )
    
    
def register(dp: Dispatcher) -> None:
    dp.include_router(router)