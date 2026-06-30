import asyncio

from src.filters.admin import IsAdminFilter
import src.keyboards.keyboards as kb
from aiogram import Bot, Dispatcher, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from src.container import container
from src.states.admin import AdminStates

router = Router()
router.message.filter(F.chat.type == "private")
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())

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
        f"📋 <b>Карточка пользователя #{user['user_id']}</b>\n\n"
        f"🔹 <b>Пользователь:</b> {mention}\n"
        f"🔹 <b>Telegram ID:</b> <code>{user['telegram_id']}</code>\n"
        f"🔹 <b>Уровень:</b> {user['level']}\n"
        f"🔹 <b>Статус:</b> {banned_status}\n"
        f"🔹 <b>Роль:</b> {admin_status}\n"
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
        parse_mode="HTML"
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
    
@router.callback_query(F.data.startswith("admin_direction_list"))
async def admin_direction_list_handler(callback_query: CallbackQuery):
    if not isinstance(callback_query.message, Message):
        return
    await callback_query.answer()
    
    directions = await container.direction_service.get_directions()
    
    await callback_query.message.edit_text(
        f"Список доступных направлений:",
        reply_markup=kb.get_direction_list_keyboard(directions)
    )
    
@router.callback_query(F.data.startswith("admin_direction_info_"))
async def admin_direction_info_handler(callback_query: CallbackQuery, state: FSMContext):
    if not isinstance(callback_query.message, Message):
        return
    await callback_query.answer()
    await state.clear()
    
    data = callback_query.data
    if not data:
        return
    
    data_parts = data.split("_")
    telegram_chat_id = int(data_parts[3])
    
    direction = await container.direction_service.get_direction(telegram_chat_id)
    
    requires_screening = "Да" if direction["requires_screening"] else "Нет"
    profile_text = (
        f"📋 <b>Направление:</b> {direction["name"]}\n\n"
        f"🔹 <b>Владелец:</b> @{direction["owner_username"]}\n"
        f"🔹 <b>Требуется ли скрининг:</b> {requires_screening}\n"
    )
    
    action_builder = InlineKeyboardBuilder()
    
    screening_text = "Убрать" if direction["requires_screening"] else "Добавить"
    
    action_builder.row(InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="admin_direction_list"))
    action_builder.row(InlineKeyboardButton(
        text="✍️ Редактировать название",
        callback_data=f"admin_direction_name_{telegram_chat_id}"
    ))
    action_builder.row(InlineKeyboardButton(
        text="🧑‍💻 Редактировать владельца",
        callback_data=f"admin_direction_owner_{telegram_chat_id}"
    ))
    action_builder.row(InlineKeyboardButton(
        text=f"🧑‍🏫 {screening_text} скрининг",
        callback_data=f"admin_direction_screening_{telegram_chat_id}"
    ))
    
    await callback_query.message.edit_text(
        text=profile_text,
        reply_markup=action_builder.as_markup(),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("admin_direction_screening_"))
async def admin_direction_screening_handler(callback_query: CallbackQuery):
    if not isinstance(callback_query.message, Message):
        return
    await callback_query.answer()
    
    data = callback_query.data
    if not data:
        return
    
    data_parts = data.split("_")
    telegram_chat_id = int(data_parts[3])
    
    direction = await container.direction_service.get_direction(telegram_chat_id)
    
    name = direction["name"]
    requires_screening = direction["requires_screening"]
    owner_username = direction["owner_username"]
    
    try:
        await container.direction_service.update_direction(
            name=name,
            owner_username=owner_username,
            requires_screening=not requires_screening,
            telegram_chat_id=telegram_chat_id
        )
        
        await callback_query.message.edit_text(
            "✅ Необходимость скрининга успешно обновлено.",
            reply_markup=kb.get_direction_card_keyboard(telegram_chat_id)
        )
    
    except Exception as e:
        await callback_query.message.edit_text(
            f"❌ Произошла ошибка при обновлении на бэкенде: {e}\nПопробуйте ввести заново:",
            reply_markup=kb.get_direction_card_keyboard(telegram_chat_id)
        )

@router.callback_query(F.data.startswith("admin_direction_owner_"))
async def admin_direction_owner_handler(callback_query: CallbackQuery, state: FSMContext):
    if not isinstance(callback_query.message, Message):
        return
    await callback_query.answer()
    
    data = callback_query.data
    if not data:
        return
    
    data_parts = data.split("_")
    telegram_chat_id = int(data_parts[3])

    await state.set_state(AdminStates.waiting_for_direction_owner)
    
    await state.update_data(edit_telegram_chat_id=telegram_chat_id)
    
    await callback_query.message.edit_text(
        "📝 Пожалуйста, введите и отправьте username нового владельца.",
        reply_markup=kb.get_direction_card_keyboard(telegram_chat_id)
    )
    
@router.message(AdminStates.waiting_for_direction_owner, F.text)
async def process_new_direction_owner(message: Message, state: FSMContext, bot: Bot):
    if not message.text:
        return
    
    state_data = await state.get_data()
    telegram_chat_id = state_data.get("edit_telegram_chat_id")
    
    if not telegram_chat_id:
        return
    
    direction = await container.direction_service.get_direction(telegram_chat_id)
    
    name = direction["name"]
    requires_screening = direction["requires_screening"]
    
    if not telegram_chat_id:
        return
    
    new_owner = message.text.strip()
    if new_owner.startswith("@"):
        new_owner = new_owner[1:]
    
    if len(new_owner) > 64:
        await message.answer("❌ Юзернейм слишком длинный (максимум 64 символов). Попробуйте еще раз:")
        return

    try:
        await container.direction_service.update_direction(
            name=name,
            owner_username=new_owner,
            requires_screening=requires_screening,
            telegram_chat_id=telegram_chat_id
        )
        
        await state.clear()
        
        await message.answer(
            text="✅ Владелец направления успешно обновлен.",
            reply_markup=kb.get_direction_card_keyboard(telegram_chat_id),
        )
        
        await asyncio.sleep(0.5)
        
        await message.delete()
        
    except Exception as e:
        await message.answer(f"❌ Произошла ошибка при обновлении на бэкенде: {e}\nПопробуйте ввести заново:")
    
@router.callback_query(F.data.startswith("admin_direction_name_"))
async def admin_direction_name_handler(callback_query: CallbackQuery, state: FSMContext):
    if not isinstance(callback_query.message, Message):
        return
    await callback_query.answer()
    
    data = callback_query.data
    if not data:
        return
    
    data_parts = data.split("_")
    telegram_chat_id = int(data_parts[3])

    await state.set_state(AdminStates.waiting_for_direction_name)
    
    await state.update_data(edit_telegram_chat_id=telegram_chat_id)
    
    await callback_query.message.edit_text(
        "📝 Пожалуйста, введите и отправьте новое название для этого направления.",
        reply_markup=kb.get_direction_card_keyboard(telegram_chat_id)
    )
    
@router.message(AdminStates.waiting_for_direction_name, F.text)
async def process_new_direction_name(message: Message, state: FSMContext, bot: Bot):
    if not message.text:
        return
    
    state_data = await state.get_data()
    telegram_chat_id = state_data.get("edit_telegram_chat_id")
    
    if not telegram_chat_id:
        return
    
    direction = await container.direction_service.get_direction(telegram_chat_id)
    
    owner_username = direction["owner_username"]
    requires_screening = direction["requires_screening"]
    
    if not telegram_chat_id:
        return
    
    new_name = message.text.strip()
    
    if len(new_name) > 255:
        await message.answer("❌ Название слишком длинное (максимум 255 символов). Попробуйте еще раз:")
        return

    try:
        await container.direction_service.update_direction(
            name=new_name,
            owner_username=owner_username,
            requires_screening=requires_screening,
            telegram_chat_id=telegram_chat_id
        )
        
        await state.clear()
        
        await message.answer(
            text="✅ Название направления успешно изменено.",
            reply_markup=kb.get_direction_card_keyboard(telegram_chat_id),
        )

        await asyncio.sleep(0.5)
        
        await message.delete()
        
    except Exception as e:
        await message.answer(f"❌ Произошла ошибка при обновлении на бэкенде: {e}\nПопробуйте ввести заново:")
    
def register(dp: Dispatcher) -> None:
    dp.include_router(router)