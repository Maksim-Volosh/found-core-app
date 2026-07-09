import asyncio
from datetime import datetime, timezone

import src.keyboards.keyboards as kb
from aiogram import Bot, Dispatcher, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from src.container import container
from src.middlewares.admin import AdminCheckMiddleware
from src.middlewares.auth import AuthMiddleware
from src.states.admin import AdminStates

admin_router = Router()
admin_router.message.filter(F.chat.type == "private")
admin_router.callback_query.filter(F.message.chat.type == "private")
admin_router.message.middleware(AuthMiddleware())
admin_router.callback_query.middleware(AuthMiddleware())
admin_router.message.middleware(AdminCheckMiddleware())
admin_router.callback_query.middleware(AdminCheckMiddleware())


@admin_router.callback_query(F.data == "admin_get_users")
async def show_users_list(callback_query: CallbackQuery) -> None:
    if not isinstance(callback_query.message, Message):
        return

    await callback_query.answer()

    all_users = await container.admin_service.get_all_users()

    await callback_query.message.edit_text(
        f"Выберите пользователя для управления:",
        reply_markup=kb.get_users_list_keyboard(
            all_users, telegram_id=callback_query.from_user.id, page=1
        ),
    )


@admin_router.callback_query(F.data.startswith("users_page_"))
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
        reply_markup=kb.get_users_list_keyboard(
            all_users, telegram_id=callback_query.from_user.id, page=page
        ),
    )


@admin_router.callback_query(F.data.startswith("admin_user_"))
async def show_user_profile_handler(
    callback_query: CallbackQuery, is_user_superadmin: bool
):
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

    user = await container.user_service.get_user_info(user["user_id"])

    if user["is_superadmin"] and not is_user_superadmin:
        await callback_query.message.edit_text(
            "❌ Вы не можете управлять супер-администратором.",
            reply_markup=kb.get_back_to_admin_keyboard(),
        )
        return
    if user["is_admin"] and not is_user_superadmin:
        await callback_query.message.edit_text(
            "❌ Вы не можете управлять администратором.",
            reply_markup=kb.get_back_to_admin_keyboard(),
        )
        return

    last_name = f" {user['last_name']}" if user.get("last_name") else ""
    full_name = f"{user['first_name']}{last_name}"

    if user.get("username"):
        mention = f"{full_name} (@{user['username']})"
    else:
        mention = f"[{full_name}](tg://user?id={user['telegram_id']})"

    banned_status = "🔴 ЗАБАНЕН" if user["is_banned"] else "🟢 Активен"
    admin_status = "👑 Админ" if user["is_admin"] else "👤 Юзер"
    superadmin_status = "👑 Супер-админ" if user["is_superadmin"] else None

    profile_text = (
        f"📋 <b>Карточка пользователя #{user['user_id']}</b>\n\n"
        f"🔹 <b>Пользователь:</b> {mention}\n"
        f"🔹 <b>Telegram ID:</b> <code>{user['telegram_id']}</code>\n"
        f"🔹 <b>Уровень:</b> {user['level']}\n"
        f"🔹 <b>Статус:</b> {banned_status}\n"
        f"🔹 <b>Роль:</b> {superadmin_status if superadmin_status else admin_status}\n\n"
    )

    status = "❌ Нет подписки"
    if user["subscription"]:
        if user["subscription"]["status"] == "ACTIVE":
            status = "✅ Активна"
        elif user["subscription"]["status"] == "EXPIRED":
            status = "❌ Просрочена"

    if status == "✅ Активна":
        date_string = user["subscription"]["expires_at"]
        dt_object = datetime.fromisoformat(date_string.replace("Z", "+00:00"))
        end_date_time = dt_object.strftime("%d %B")

        start_date_string = user["subscription"]["started_at"]
        start_dt_object = datetime.fromisoformat(
            start_date_string.replace("Z", "+00:00")
        )
        start_date_time = start_dt_object.strftime("%d %B")

        days_remaining = (dt_object - datetime.now(timezone.utc)).days
        hours_remaining = (dt_object - datetime.now(timezone.utc)).seconds // 3600
        minutes_remaining = (
            (dt_object - datetime.now(timezone.utc)).seconds // 60
        ) % 60

        profile_text += (
            f"🔹 Статус подписки: <b>{status}</b>\n"
            f"🔹 Дата начала подписки: <b>{start_date_time}</b> \n🔹 Дата окончания подписки: <b>{end_date_time}</b>"
            f"\n🚀 До окончания подписки осталось: \n<u><b>{days_remaining}</b></u> дн. <u><b>{hours_remaining}</b></u> ч. <u><b>{minutes_remaining}</b></u> мин."
        )
    if status == "❌ Просрочена":
        date_string = user["subscription"]["expires_at"]
        dt_object = datetime.fromisoformat(date_string.replace("Z", "+00:00"))
        end_date_time = dt_object.strftime("%d %B")

        start_date_string = user["subscription"]["started_at"]
        start_dt_object = datetime.fromisoformat(
            start_date_string.replace("Z", "+00:00")
        )
        start_date_time = start_dt_object.strftime("%d %B")

        profile_text += (
            f"🔹 Статус подписки: <b>{status}</b>\n"
            f"🔹 Дата начала подписки: <b>{start_date_time}</b> \n🔹 Дата окончания подписки: <b>{end_date_time}</b>"
        )

    if status == "❌ Нет подписки":
        profile_text += f"🔹 <b>Подписка:</b> ❌ Нет подписки\n"

    action_builder = InlineKeyboardBuilder()

    ban_text = "🟢 Разбанить" if user["is_banned"] else "🔴 Забанить"
    ban_decision = 0 if user["is_banned"] else 1
    level = user["level"]

    action_builder.row(
        InlineKeyboardButton(
            text=ban_text,
            callback_data=f"toggle_ban_{user_id}_{ban_decision}_{current_page}",
        )
    )
    action_builder.row(
        InlineKeyboardButton(
            text="🥇 Поменять уровень",
            callback_data=f"toggle_level_{user_id}_{level}_{current_page}",
        )
    )
    action_builder.row(
        InlineKeyboardButton(
            text="🚀 Доступ к направлению",
            callback_data=f"toggle_direction_{user_id}_{current_page}",
        )
    )
    action_builder.row(
        InlineKeyboardButton(
            text="🔖 Выдать подписку",
            callback_data=f"toggle_subscription_{user["user_id"]}_{current_page}",
        )
    )
    if is_user_superadmin:
        decision = 0 if admin_status == "👑 Админ" else 1
        text = "🧢 Снять администратора" if decision == 0 else "👑 Сделать админом"
        action_builder.row(
            InlineKeyboardButton(
                text=text,
                callback_data=f"toggle_admin_{user["user_id"]}_{current_page}_{decision}",
            )
        )
    action_builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад к списку", callback_data=f"users_page_{current_page}"
        )
    )

    await callback_query.message.edit_text(
        text=profile_text, reply_markup=action_builder.as_markup(), parse_mode="HTML"
    )


@admin_router.callback_query(F.data.startswith("toggle_direction_"))
async def toggle_direction_handler(callback_query: CallbackQuery):
    if not isinstance(callback_query.message, Message):
        return
    await callback_query.answer()

    data = callback_query.data
    if not data:
        return

    data_parts = data.split("_")
    user_id = int(data_parts[2])
    current_page = int(data_parts[3]) if len(data_parts) > 3 else 1

    directions = await container.direction_service.get_directions()

    await callback_query.message.edit_text(
        f"Пожалуйста, выберите направление к которому вы хотите поменять доступ.",
        reply_markup=kb.get_direction_list_access_keyboard(
            directions, user_id, current_page
        ),
    )


@admin_router.callback_query(F.data.startswith("admin_direction_access_"))
async def admin_direction_access_handler(callback_query: CallbackQuery):
    if not isinstance(callback_query.message, Message):
        return
    await callback_query.answer()

    data = callback_query.data
    if not data:
        return

    data_parts = data.split("_")
    telegram_chat_id = int(data_parts[3])
    user_id = int(data_parts[4])
    current_page = int(data_parts[5]) if len(data_parts) > 3 else 1

    direction_access_response = await container.direction_service.get_direction_access(
        user_id, telegram_chat_id
    )
    if direction_access_response is None:
        created_direction_access = (
            await container.direction_service.create_direction_access(
                user_id, telegram_chat_id
            )
        )
        direction_access = created_direction_access["screening_status"]
    else:
        direction_access = direction_access_response["screening_status"]

    new_direction_access = (
        "APPROVED" if direction_access == "NOT_STARTED" else "NOT_STARTED"
    )
    await container.admin_service.update_user_direction_access(
        user_id, telegram_chat_id, new_direction_access
    )

    result_text = "разрешен" if new_direction_access == "APPROVED" else "запрещен"
    await callback_query.message.edit_text(
        f"Доступ к направлению для пользователя успешно {result_text}.",
        reply_markup=kb.get_back_to_user_keyboard(user_id, current_page),
    )


@admin_router.callback_query(F.data.startswith("toggle_admin_"))
async def toggle_admin_handler(callback_query: CallbackQuery):
    if not isinstance(callback_query.message, Message):
        return
    await callback_query.answer()

    data = callback_query.data
    if not data:
        return

    data_parts = data.split("_")
    user_id = int(data_parts[2])
    current_page = int(data_parts[3]) if len(data_parts) > 3 else 1
    decision = True if data_parts[4] == "1" else False

    await container.admin_service.toggle_admin(user_id, decision)

    text = "👑 Админ" if decision else "👤 Пользователь"

    await callback_query.message.edit_text(
        f"Статус пользователя успешно назначен как {text}.",
        reply_markup=kb.get_back_to_user_keyboard(user_id, current_page),
    )


@admin_router.callback_query(F.data.startswith("toggle_level_"))
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
        reply_markup=kb.get_user_levels_keyboard(user_id, level, current_page),
    )


@admin_router.callback_query(F.data.startswith("admin_level_"))
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
        reply_markup=kb.get_back_to_user_keyboard(user_id, current_page),
    )


@admin_router.callback_query(F.data.startswith("toggle_ban_"))
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
        reply_markup=kb.get_back_to_user_keyboard(user_id, current_page),
    )


@admin_router.callback_query(F.data.startswith("toggle_subscription_"))
async def toggle_subscription_handler(callback_query: CallbackQuery):
    if not isinstance(callback_query.message, Message):
        return
    await callback_query.answer()

    data = callback_query.data
    if not data:
        return

    data_parts = data.split("_")
    user_id = int(data_parts[2])
    current_page = int(data_parts[3]) if len(data_parts) > 3 else 1

    await callback_query.message.edit_text(
        f"Выберите на сколько месяцев вы хотите продлить подписку.",
        reply_markup=kb.get_admin_months_keyboard(user_id, current_page),
    )


@admin_router.callback_query(F.data.startswith("give_subscription_"))
async def give_subscription_handler(callback_query: CallbackQuery):
    if not isinstance(callback_query.message, Message):
        return
    await callback_query.answer()

    data = callback_query.data
    if not data:
        return

    data_parts = data.split("_")
    user_id = int(data_parts[2])
    current_page = int(data_parts[3]) if len(data_parts) > 3 else 1
    months = int(data_parts[4]) if len(data_parts) > 4 else 1

    await container.admin_service.give_subscription(user_id, months)

    await callback_query.message.edit_text(
        f"Подписка успешно продлена на {months} месяц(ов).",
        reply_markup=kb.get_back_to_user_keyboard(user_id, current_page),
    )


@admin_router.callback_query(F.data.startswith("admin_direction_list"))
async def admin_direction_list_handler(callback_query: CallbackQuery):
    if not isinstance(callback_query.message, Message):
        return
    await callback_query.answer()

    directions = await container.direction_service.get_directions()

    await callback_query.message.edit_text(
        f"Список доступных направлений:",
        reply_markup=kb.get_direction_list_keyboard(directions),
    )


@admin_router.callback_query(F.data.startswith("admin_direction_info_"))
async def admin_direction_info_handler(
    callback_query: CallbackQuery, state: FSMContext
):
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

    action_builder.row(
        InlineKeyboardButton(
            text="✍️ Редактировать название",
            callback_data=f"admin_direction_name_{telegram_chat_id}",
        )
    )
    action_builder.row(
        InlineKeyboardButton(
            text="🧑‍💻 Редактировать владельца",
            callback_data=f"admin_direction_owner_{telegram_chat_id}",
        )
    )
    action_builder.row(
        InlineKeyboardButton(
            text=f"🧑‍🏫 {screening_text} скрининг",
            callback_data=f"admin_direction_screening_{telegram_chat_id}",
        )
    )
    action_builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад к списку", callback_data="admin_direction_list"
        )
    )

    await callback_query.message.edit_text(
        text=profile_text, reply_markup=action_builder.as_markup(), parse_mode="HTML"
    )


@admin_router.callback_query(F.data.startswith("admin_direction_screening_"))
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
            telegram_chat_id=telegram_chat_id,
        )

        await callback_query.message.edit_text(
            "✅ Необходимость скрининга успешно обновлено.",
            reply_markup=kb.get_direction_card_keyboard(telegram_chat_id),
        )

    except Exception as e:
        await callback_query.message.edit_text(
            f"❌ Произошла ошибка при обновлении на бэкенде: {e}\nПопробуйте ввести заново:",
            reply_markup=kb.get_direction_card_keyboard(telegram_chat_id),
        )


@admin_router.callback_query(F.data.startswith("admin_direction_owner_"))
async def admin_direction_owner_handler(
    callback_query: CallbackQuery, state: FSMContext
):
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
        reply_markup=kb.get_direction_card_keyboard(telegram_chat_id),
    )


@admin_router.message(AdminStates.waiting_for_direction_owner, F.text)
async def process_new_direction_owner(message: Message, state: FSMContext):
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
        await message.answer(
            "❌ Юзернейм слишком длинный (максимум 64 символов). Попробуйте еще раз:"
        )
        return

    try:
        await container.direction_service.update_direction(
            name=name,
            owner_username=new_owner,
            requires_screening=requires_screening,
            telegram_chat_id=telegram_chat_id,
        )

        await state.clear()

        await message.answer(
            text="✅ Владелец направления успешно обновлен.",
            reply_markup=kb.get_direction_card_keyboard(telegram_chat_id),
        )

        await asyncio.sleep(0.5)

        await message.delete()

    except Exception as e:
        await message.answer(
            f"❌ Произошла ошибка при обновлении на бэкенде: {e}\nПопробуйте ввести заново:"
        )


@admin_router.callback_query(F.data.startswith("admin_direction_name_"))
async def admin_direction_name_handler(
    callback_query: CallbackQuery, state: FSMContext
):
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
        reply_markup=kb.get_direction_card_keyboard(telegram_chat_id),
    )


@admin_router.message(AdminStates.waiting_for_direction_name, F.text)
async def process_new_direction_name(message: Message, state: FSMContext):
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
        await message.answer(
            "❌ Название слишком длинное (максимум 255 символов). Попробуйте еще раз:"
        )
        return

    try:
        await container.direction_service.update_direction(
            name=new_name,
            owner_username=owner_username,
            requires_screening=requires_screening,
            telegram_chat_id=telegram_chat_id,
        )

        await state.clear()

        await message.answer(
            text="✅ Название направления успешно изменено.",
            reply_markup=kb.get_direction_card_keyboard(telegram_chat_id),
        )

        await asyncio.sleep(0.5)

        await message.delete()

    except Exception as e:
        await message.answer(
            f"❌ Произошла ошибка при обновлении на бэкенде: {e}\nПопробуйте ввести заново:"
        )


@admin_router.callback_query(F.data.startswith("admin_find_user"))
async def admin_find_user_handler(callback_query: CallbackQuery, state: FSMContext):
    if not isinstance(callback_query.message, Message):
        return
    await callback_query.answer()

    await state.set_state(AdminStates.waiting_for_user_username)

    await callback_query.message.edit_text(
        "📝 Пожалуйста, введите и отправьте юзернейм пользователя.",
        reply_markup=kb.get_back_to_admin_keyboard(),
    )


@admin_router.message(AdminStates.waiting_for_user_username, F.text)
async def process_user_username(
    message: Message, is_user_superadmin: bool, state: FSMContext
):
    if not message.text:
        return

    username = message.text.strip()
    if username.startswith("@"):
        username = username[1:]

    if len(username) > 64:
        await message.answer(
            "❌ Юзернейм слишком длинный (максимум 64 символов). Попробуйте еще раз:"
        )
        return

    user = await container.admin_service.get_user_by_username(username)
    if not user:
        await message.answer("❌ Пользователь не найден. Попробуйте еще раз:")
        return

    await state.clear()
    user = await container.user_service.get_user_info(user["user_id"])

    if user["is_superadmin"] and not is_user_superadmin:
        await message.answer(
            "❌ Вы не можете управлять супер-администратором.",
            reply_markup=kb.get_back_to_admin_keyboard(),
        )
        return
    if user["is_admin"] and not is_user_superadmin:
        await message.answer(
            "❌ Вы не можете управлять администратором.",
            reply_markup=kb.get_back_to_admin_keyboard(),
        )
        return

    last_name = f" {user['last_name']}" if user.get("last_name") else ""
    full_name = f"{user['first_name']}{last_name}"

    if user.get("username"):
        mention = f"{full_name} (@{user['username']})"
    else:
        mention = f"[{full_name}](tg://user?id={user['telegram_id']})"

    banned_status = "🔴 ЗАБАНЕН" if user["is_banned"] else "🟢 Активен"
    admin_status = "👑 Админ" if user["is_admin"] else "👤 Юзер"
    superadmin_status = "👑 Супер-админ" if user["is_superadmin"] else None

    profile_text = (
        f"📋 <b>Карточка пользователя #{user['user_id']}</b>\n\n"
        f"🔹 <b>Пользователь:</b> {mention}\n"
        f"🔹 <b>Telegram ID:</b> <code>{user['telegram_id']}</code>\n"
        f"🔹 <b>Уровень:</b> {user['level']}\n"
        f"🔹 <b>Статус:</b> {banned_status}\n"
        f"🔹 <b>Роль:</b> {superadmin_status if superadmin_status else admin_status}\n\n"
    )

    status = "❌ Нет подписки"
    if user["subscription"]:
        if user["subscription"]["status"] == "ACTIVE":
            status = "✅ Активна"
        elif user["subscription"]["status"] == "EXPIRED":
            status = "❌ Просрочена"

    if status == "✅ Активна":
        date_string = user["subscription"]["expires_at"]
        dt_object = datetime.fromisoformat(date_string.replace("Z", "+00:00"))
        end_date_time = dt_object.strftime("%d %B")

        start_date_string = user["subscription"]["started_at"]
        start_dt_object = datetime.fromisoformat(
            start_date_string.replace("Z", "+00:00")
        )
        start_date_time = start_dt_object.strftime("%d %B")

        days_remaining = (dt_object - datetime.now(timezone.utc)).days
        hours_remaining = (dt_object - datetime.now(timezone.utc)).seconds // 3600
        minutes_remaining = (
            (dt_object - datetime.now(timezone.utc)).seconds // 60
        ) % 60

        profile_text += (
            f"🔹 Статус подписки: <b>{status}</b>\n"
            f"🔹 Дата начала подписки: <b>{start_date_time}</b> \n🔹 Дата окончания подписки: <b>{end_date_time}</b>"
            f"\n🚀 До окончания подписки осталось: \n<u><b>{days_remaining}</b></u> дн. <u><b>{hours_remaining}</b></u> ч. <u><b>{minutes_remaining}</b></u> мин."
        )
    if status == "❌ Просрочена":
        date_string = user["subscription"]["expires_at"]
        dt_object = datetime.fromisoformat(date_string.replace("Z", "+00:00"))
        end_date_time = dt_object.strftime("%d %B")

        start_date_string = user["subscription"]["started_at"]
        start_dt_object = datetime.fromisoformat(
            start_date_string.replace("Z", "+00:00")
        )
        start_date_time = start_dt_object.strftime("%d %B")

        profile_text += (
            f"🔹 Статус подписки: <b>{status}</b>\n"
            f"🔹 Дата начала подписки: <b>{start_date_time}</b> \n🔹 Дата окончания подписки: <b>{end_date_time}</b>"
        )

    if status == "❌ Нет подписки":
        profile_text += f"🔹 <b>Подписка:</b> ❌ Нет подписки\n"

    action_builder = InlineKeyboardBuilder()

    ban_text = "🟢 Разбанить" if user["is_banned"] else "🔴 Забанить"
    ban_decision = 0 if user["is_banned"] else 1
    level = user["level"]

    current_page = 1  # Default to page 1 since we are searching by username
    action_builder.row(
        InlineKeyboardButton(
            text=ban_text,
            callback_data=f"toggle_ban_{user["user_id"]}_{ban_decision}_{current_page}",
        )
    )
    action_builder.row(
        InlineKeyboardButton(
            text="🥇 Поменять уровень",
            callback_data=f"toggle_level_{user["user_id"]}_{level}_{current_page}",
        )
    )
    action_builder.row(
        InlineKeyboardButton(
            text="🚀 Доступ к направлению",
            callback_data=f"toggle_direction_{user["user_id"]}_{current_page}",
        )
    )
    action_builder.row(
        InlineKeyboardButton(
            text="🔖 Выдать подписку",
            callback_data=f"toggle_subscription_{user["user_id"]}_{current_page}",
        )
    )
    if is_user_superadmin:
        decision = 0 if admin_status == "👑 Админ" else 1
        text = "🧢 Снять администратора" if decision == 0 else "👑 Сделать админом"
        action_builder.row(
            InlineKeyboardButton(
                text=text,
                callback_data=f"toggle_admin_{user["user_id"]}_{current_page}_{decision}",
            )
        )
    action_builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data=f"admin_back_to_main")
    )

    await message.answer(
        text=profile_text, reply_markup=action_builder.as_markup(), parse_mode="HTML"
    )


def register(dp: Dispatcher) -> None:
    dp.include_router(admin_router)
