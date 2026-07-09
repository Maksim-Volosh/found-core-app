from datetime import datetime

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.filters.chat_member_updated import ChatMemberUpdatedFilter, JOIN_TRANSITION
from aiogram.types import ChatMemberUpdated
from config import MAIN_CHAT_ID
from src.container import container
import src.keyboards.keyboards as kb
from aiogram.types import CallbackQuery, ChatMemberUpdated, Message
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest

router = Router()
router.message.filter(F.chat.type == "private")
router.callback_query.filter(F.message.chat.type == "private")


async def is_user_in_chat(bot: Bot, chat_id: int, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)

        if member.status in [
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.CREATOR,
        ]:
            return True

        return False

    except TelegramBadRequest as e:
        if "user not found" in str(e).lower():
            return False

        print(f"Ошибка проверки пользователя в чате: {e}")
        return False

@router.message(CommandStart(), F.chat.type == "private")
async def command_start_handler(
    message: Message,
    bot: Bot,
) -> None:
    if message.from_user and message.from_user.username:
        admin_service = container.admin_service
        user = await admin_service.get_user_by_username(message.from_user.username)
        if user:
            if user["is_superadmin"]:
                welcome_text = (
                    f"Привет, <b>{message.from_user.first_name}</b>!\n\n"
                )
                reply_markup = kb.get_superadmin_main_keyboard()
                await message.answer(welcome_text, reply_markup=reply_markup, parse_mode="HTML")
            elif user["is_admin"]:
                welcome_text = (
                    f"Привет, <b>{message.from_user.first_name}</b>!\n\n"
                )
                reply_markup = kb.get_admin_main_keyboard()
                await message.answer(welcome_text, reply_markup=reply_markup, parse_mode="HTML")
            else:
                welcome_text = (
                    f"Привет, <b>{message.from_user.first_name}</b>!\n\n"
                    "<b>Добро пожаловать в команду FoundCore!</b> 👋\n\n"
                    "Вы уже зарегистрированы в FoundCore. "
                )
        else:
            if await is_user_in_chat(bot, MAIN_CHAT_ID, message.from_user.id):
                auth_service = container.auth_service
                await auth_service.auth(
                    {
                        "username": message.from_user.username,
                        "first_name": message.from_user.first_name,
                        "last_name": message.from_user.last_name,
                    },
                    message.from_user.id,
                )
                welcome_text = (
                    f"Привет, <b>{message.from_user.first_name}</b>!\n\n"
                    "<b>Добро пожаловать в команду FoundCore!</b> 👋\n\n"
                    "Вы успешно зарегистрировались в FoundCore. Спасибо!"
                )
            else:
                welcome_text = (
                    f"Привет, <b>{message.from_user.first_name}</b>!\n\n"
                    "<b>Добро пожаловать в команду FoundCore!</b> 👋\n\n"
                    "Так как вас нету в нашем сообществе вы пока не можете использовать бота. Подождите пока миграция закончится."
                )
        await message.answer(welcome_text, parse_mode="HTML")
    else:
        await message.answer(
            "В вашем профиле нету юзернейма. Пожалуйста, установите его и повторите попытку."
        )
        
# @router.message(CommandStart(), F.chat.type == "private")
# async def command_start_handler(
#     message: Message,
#     is_user_admin: bool,
#     is_user_superadmin: bool,
#     backend_user_id: int,
# ) -> None:
#     if message.from_user:
#         access_service = container.access_service
#         access_response = await access_service.check_main_access(backend_user_id)
#         access = access_response["allowed"]

#         welcome_text = (
#             f"Привет, <b>{message.from_user.first_name}</b>!\n\n"
#             "<b>Добро пожаловать в команду FoundCore!</b> 👋\n\n"
#             "Одно нужное знакомство способно перевернуть год работы в одиночку. "
#             "Мы верим в это, потому что проверили на себе. "
#             "FoundCore — это не просто Telegram-сообщество, это среда людей, "
#             "которые видят возможности там, где другие видят проблемы.\n\n"
#             "Если вы устали от случайных знакомств в пустых чатах и ищете тех, "
#             "кто действительно разделяет ваше стремление к развитию, то вы в "
#             "правильном месте. Мы создали платформу, где каждый участник ценен "
#             "своими знаниями, энергией и готовностью двигаться вперед."
#         )
#         if is_user_superadmin:
#             reply_markup = kb.get_superadmin_main_keyboard()
#         elif is_user_admin:
#             reply_markup = kb.get_admin_main_keyboard()
#         elif not access:
#             reply_markup = kb.get_guest_main_keyboard()
#         else:
#             reply_markup = kb.get_resident_main_keyboard()

#         await message.answer(welcome_text, reply_markup=reply_markup, parse_mode="HTML")


def register(dp: Dispatcher) -> None:
    dp.include_router(router)
