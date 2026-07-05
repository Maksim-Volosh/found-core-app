from datetime import datetime, timezone
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
router.callback_query.filter(F.message.chat.type == "private")


@router.callback_query(F.data == "guest_profile")
async def guest_profile_handler(
    callback_query: CallbackQuery, backend_user_id: int
) -> None:
    if not isinstance(callback_query.message, Message):
        return

    await callback_query.answer()
    user_data = await container.user_service.get_user_info(backend_user_id)

    if user_data is None:
        text = "❌ Вы были заблокированы в данном сообществе. \n\nПожалуйста, обратитесь к администратору для получения дополнительной информации."
        await callback_query.message.answer(text, parse_mode="Markdown")
        return

    await callback_query.message.edit_text(
        f"Привет, {user_data['first_name']}! \n\nВаш уровень в сообществе: {user_data['level']}/10",
        reply_markup=kb.get_guest_back_keyboard(),
    )


@router.callback_query(F.data == "resident_profile")
async def resident_profile_handler(
    callback_query: CallbackQuery, backend_user_id: int
) -> None:
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
            reply_markup=kb.get_guest_back_keyboard(),
        )
        return

    if user_data["subscription"]["status"] == "EXPIRED":
        await callback_query.message.edit_text(
            f"Привет, {user_data['first_name']}! \n\nВаш уровень в сообществе: {user_data['level']}/10",
            reply_markup=kb.get_guest_back_keyboard(),
        )
        return

    date_string = user_data["subscription"]["expires_at"]
    dt_object = datetime.fromisoformat(date_string.replace("Z", "+00:00"))
    end_date_time = dt_object.strftime("%d %B")

    start_date_string = user_data["subscription"]["started_at"]
    start_dt_object = datetime.fromisoformat(start_date_string.replace("Z", "+00:00"))
    start_date_time = start_dt_object.strftime("%d %B")

    days_remaining = (dt_object - datetime.now(timezone.utc)).days
    hours_remaining = (dt_object - datetime.now(timezone.utc)).seconds // 3600
    minutes_remaining = ((dt_object - datetime.now(timezone.utc)).seconds // 60) % 60

    edit_text = (
        f"Привет, {user_data['first_name']}! \n\n🥇 Ваш уровень в сообществе: <b>{user_data['level']}/10</b>"
        f"\n🎯 Дата начала подписки: <b>{start_date_time}</b> \n🎯 Дата окончания подписки: <b>{end_date_time}</b>"
        f"\n🚀 До окончания подписки осталось: \n<u><b>{days_remaining}</b></u> дн. <u><b>{hours_remaining}</b></u> ч. <u><b>{minutes_remaining}</b></u> мин."
        f"\n\n📎 <i>Учтите что дата начала и окончания подписки может отличаться от даты оплаты из за разницы часовых поясов (отображаемый UTC). После оплаты вы гарантированно получаете доступ к сообществу, на срок, выбранный при оплате.</i>"
    )

    await callback_query.message.edit_text(
        text=edit_text, reply_markup=kb.get_resident_back_keyboard(), parse_mode="HTML"
    )


def register(dp: Dispatcher) -> None:
    dp.include_router(router)
