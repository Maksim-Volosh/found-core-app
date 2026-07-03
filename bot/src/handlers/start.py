from datetime import datetime

from aiogram import Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.filters.chat_member_updated import ChatMemberUpdatedFilter, JOIN_TRANSITION
from aiogram.types import ChatMemberUpdated
from src.container import container
import src.keyboards.keyboards as kb

router = Router()
router.message.filter(F.chat.type == "private")
router.callback_query.filter(F.message.chat.type == "private")

@router.message(CommandStart(), F.chat.type == "private")
async def command_start_handler(message: Message, is_user_admin: bool, is_user_superadmin: bool, backend_user_id: int) -> None:
    if message.from_user:
        access_service = container.access_service
        access_response = await access_service.check_main_access(backend_user_id)
        access = access_response["allowed"]
                
        welcome_text = (
            f"Привет, <b>{message.from_user.first_name}</b>!\n\n"
            "<b>Добро пожаловать в команду FoundCore!</b> 👋\n\n"
            "Одно нужное знакомство способно перевернуть год работы в одиночку. "
            "Мы верим в это, потому что проверили на себе. "
            "FoundCore — это не просто Telegram-сообщество, это среда людей, "
            "которые видят возможности там, где другие видят проблемы.\n\n"
            "Если вы устали от случайных знакомств в пустых чатах и ищете тех, "
            "кто действительно разделяет ваше стремление к развитию, то вы в "
            "правильном месте. Мы создали платформу, где каждый участник ценен "
            "своими знаниями, энергией и готовностью двигаться вперед."
        )
        if is_user_superadmin:
            reply_markup = kb.get_superadmin_main_keyboard()
        elif is_user_admin:
            reply_markup = kb.get_admin_main_keyboard()
        elif not access:
            reply_markup = kb.get_guest_main_keyboard()
        else:
            reply_markup = kb.get_resident_main_keyboard()

        await message.answer(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode="HTML"
        )



def register(dp: Dispatcher) -> None:
    dp.include_router(router)