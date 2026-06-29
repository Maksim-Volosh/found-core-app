from datetime import datetime
from typing import Any

import src.keyboards.keyboards as kb
from aiogram import Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.filters.chat_member_updated import (JOIN_TRANSITION,
                                                 ChatMemberUpdatedFilter)
from aiogram.fsm.context import FSMContext
from aiogram.types import (CallbackQuery, ChatMemberUpdated,
                           InlineKeyboardButton, InlineKeyboardMarkup, Message)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from src.container import container

router = Router()
router.message.filter(F.chat.type == "private")

@router.callback_query(F.data == "admin_get_users")
async def show_users_list(callback_query: CallbackQuery) -> None:
    if not isinstance(callback_query.message, Message):
        return
    
    await callback_query.answer()
    
    all_users = await container.admin_service.get_all_users()

    await callback_query.message.edit_text(
        f"Выберите пользователя для управления:",
        reply_markup=kb.get_users_list_keyboard(all_users, page=1)
    )

@router.callback_query(F.data.startswith("users_page_"))
async def process_users_page(callback_query: CallbackQuery):
    if not isinstance(callback_query.message, Message):
        return
    await callback_query.answer()
    
    data = callback_query.data
    if not data:
        return
    
    page = int(data.replace("users_page_", ""))
    all_users = await container.admin_service.get_all_users()

    await callback_query.message.edit_text(
        f"Выберите пользователя для управления:",
        reply_markup=kb.get_users_list_keyboard(all_users, page=page)
    )
    
@router.callback_query(F.data.startswith("admin_user_"))
async def show_user_profile_handler(callback_query: CallbackQuery):
    if not isinstance(callback_query.message, Message):
        return
    await callback_query.answer()

    data = callback_query.data
    if not data:
        return
    
    data_parts = data.split("_")
    user_id = int(data_parts[2])
    current_page = int(data_parts[3]) if len(data_parts) > 3 else 1
    
    user = await container.user_service.get_user_info(user_id)
    if not user:
        await callback_query.message.edit_text("❌ Пользователь не найден.")
        return

    last_name = f" {user['last_name']}" if user.get('last_name') else ""
    full_name = f"{user['first_name']}{last_name}"
    
    if user.get('username'):
        mention = f"{full_name} (@{user['username']})"
    else:
        mention = f"[{full_name}](tg://user?id={user['telegram_id']})"

    banned_status = "🔴 ЗАБАНЕН" if user["is_banned"] else "🟢 Активен"
    admin_status = "👑 Админ" if user["is_admin"] else "👤 Юзер"
    
    profile_text = (
        f"📋 **Карточка пользователя #{user['user_id']}**\n\n"
        f"🔹 **Пользователь:** {mention}\n"
        f"🔹 **Telegram ID:** `{user['telegram_id']}`\n"
        f"🔹 **Уровень:** {user['level']}\n"
        f"🔹 **Статус:** {banned_status}\n"
        f"🔹 **Роль:** {admin_status}\n"
    )

    action_builder = InlineKeyboardBuilder()
    
    ban_text = "🟢 Разбанить" if user["is_banned"] else "🔴 Забанить"
    ban_decision = 0 if user["is_banned"] else 1
    level = user["level"]
    
    action_builder.row(InlineKeyboardButton(text=ban_text, callback_data=f"toggle_ban_{user_id}_{ban_decision}_{current_page}"))
    action_builder.row(InlineKeyboardButton(text="🥇 Поменять уровень", callback_data=f"toggle_level_{user_id}_{level}_{current_page}"))
    action_builder.row(InlineKeyboardButton(text="⬅️ Назад к списку", callback_data=f"users_page_{current_page}"))

    await callback_query.message.edit_text(
        text=profile_text, 
        reply_markup=action_builder.as_markup(),
        parse_mode="Markdown"
    )
    
@router.callback_query(F.data.startswith("toggle_level_"))
async def toggle_user_level_handler(callback_query: CallbackQuery):
    if not isinstance(callback_query.message, Message):
        return
    await callback_query.answer()
    
    data = callback_query.data
    if not data:
        return
    
    data_parts = data.split("_")
    user_id = int(data_parts[2])
    level = int(data_parts[3])
    current_page = int(data_parts[4]) if len(data_parts) > 3 else 1
    
        
    await callback_query.message.edit_text(
        f"Пожалуйста, выберите уровень который назначить пользователю.",
        reply_markup=kb.get_user_levels_keyboard(user_id, level, current_page)
    )
    
@router.callback_query(F.data.startswith("admin_level_"))
async def admin_user_level_handler(callback_query: CallbackQuery):
    if not isinstance(callback_query.message, Message):
        return
    await callback_query.answer()
    
    data = callback_query.data
    if not data:
        return
    
    data_parts = data.split("_")
    user_id = int(data_parts[2])
    level = int(data_parts[3])
    current_page = int(data_parts[4]) if len(data_parts) > 3 else 1
    
    await container.admin_service.change_user_level(user_id, level)
        
    await callback_query.message.edit_text(
        f"Уровень пользователя успешно изменен.",
        reply_markup=kb.get_back_to_user_keyboard(user_id, current_page)
    )
    
@router.callback_query(F.data.startswith("toggle_ban_"))
async def ban_user_handler(callback_query: CallbackQuery):
    if not isinstance(callback_query.message, Message):
        return
    await callback_query.answer()
    
    data = callback_query.data
    if not data:
        return
    
    data_parts = data.split("_")
    user_id = int(data_parts[2])
    ban_decision = bool(int(data_parts[3]))
    current_page = int(data_parts[4]) if len(data_parts) > 3 else 1
    
    await container.admin_service.ban_user(user_id, ban_decision)
        
    await callback_query.message.edit_text(
        f"Пользлователь успешно {'забанен' if ban_decision else 'разбанен'}.",
        reply_markup=kb.get_back_to_user_keyboard(user_id, current_page)
    )
    
def register(dp: Dispatcher) -> None:
    dp.include_router(router)