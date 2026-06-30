import asyncio

import src.keyboards.keyboards as kb
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from src.container import container
from src.filters.admin import IsAdminFilter
from src.states.admin import AdminStates

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}))
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())
from config import SECRET_REGISTER_KEY


# Роутер уже отфильтрован на работу только в группах (как мы сделали шаг назад)
@router.message(Command("register"))
async def process_register_command(message: Message, command: CommandObject):
    if not command.args:
        await message.answer(
            "❌ Передайте аргументы!\n"
            "Формат: `/register КЛЮЧ ВЛАДЕЛЕЦ СКРИНИНГ НАЗВАНИЕ_НАПРАВЛЕНИЯ`"
        )
        return

    args = command.args.split(maxsplit=3)
        
    if len(args) < 4:
        await message.answer(
            f"❌ Недостаточно аргументов.\n"
            "Формат: `/register КЛЮЧ ВЛАДЕЛЕЦ_ЮЗЕРНЕЙМ TRUE/FALSE НАЗВАНИЕ_НАПРАВЛЕНИЯ`"
        )
        return

    key, owner_username, requires_screening_str = args[0], args[1], args[2]
    direction_name = args[3].strip()

    if key != SECRET_REGISTER_KEY:
        await message.answer("❌ Неверный секретный ключ регистрации направления.")
        await message.delete()
        return

    requires_screening = requires_screening_str.lower() in ["true", "1", "yes", "да", "True", "TRUE", "Yes", "Да"]

    owner_username = owner_username.lstrip("@")

    telegram_chat_id = message.chat.id
    
    await message.delete()

    try:
        await container.direction_service.create_direction(
            telegram_chat_id=telegram_chat_id,
            name=direction_name,
            owner_username=owner_username,
            requires_screening=requires_screening
        )

        status_text = "🔒 Требуется скрининг куратора" if requires_screening else "🟢 Автоматическая ссылка"
        
        bot_msg = await message.answer(
            f"✅ Направление успешно зарегистрировано на бэкенде!\n\n"
            f"🔹 Название: <b>{direction_name}</b>\n"
            f"🔹 ID чата: <code>{telegram_chat_id}</code>\n"
            f"🔹 Владелец: @{owner_username}\n"
            f"🔹 Режим доступа: {status_text}",
            parse_mode="HTML"
        )
        await asyncio.sleep(5)
        await bot_msg.delete()

    except Exception as e:
        error_text = str(e)
    
        if "409" in error_text:
            bot_msg = await message.answer(
                "⚠️ **Это направление уже зарегистрировано в системе!**\n"
                "Если вам нужно изменить его параметры, используйте админ-панель в ЛС бота."
            )
            await asyncio.sleep(7)
            await bot_msg.delete()
        else:
            await message.answer(f"❌ Ошибка при регистрации на сервере: {e}")
    
def register(dp: Dispatcher) -> None:
    dp.include_router(router)