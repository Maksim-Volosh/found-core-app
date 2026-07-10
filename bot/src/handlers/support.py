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


@router.callback_query(F.data == "resident_support_faq")
async def resident_support_handler(
    callback_query: CallbackQuery, backend_user_id: int
) -> None:
    if not isinstance(callback_query.message, Message):
        return

    await callback_query.answer()

    await callback_query.message.edit_text(
        text=(
            f"Если у вас возникли вопросы или проблемы, пожалуйста, обратитесь к нашей команде поддержки. Мы готовы помочь вам с любыми вопросами, связанными с нашим сообществом и услугами.\n\n"
            f"Вы можете связаться с нами через следующие каналы:\n"
            f"1. Телеграм: @zakharmot\n"
            f"2. Телеграм: @Kateu\n"
            f"По техническим причинам/багам:\n"
            f"Телеграм: @Ne_problem\n"
        ),
        reply_markup=kb.get_resident_back_keyboard(),
    )


@router.callback_query(F.data == "guest_support_faq")
async def guest_support_handler(
    callback_query: CallbackQuery, backend_user_id: int
) -> None:
    if not isinstance(callback_query.message, Message):
        return

    await callback_query.answer()

    await callback_query.message.edit_text(
        text=(
            f"Если у вас возникли вопросы или проблемы, пожалуйста, обратитесь к нашей команде поддержки. Мы готовы помочь вам с любыми вопросами, связанными с нашим сообществом и услугами.\n\n"
            f"Вы можете связаться с нами через следующие каналы:\n"
            f"1. Телеграм: @zakharmot\n"
            f"2. Телеграм: @Kateu\n"
            f"По техническим причинам/багам:\n"
            f"Телеграм: @Ne_problem\n"
        ),
        reply_markup=kb.get_guest_back_keyboard(),
    )


def register(dp: Dispatcher) -> None:
    dp.include_router(router)
