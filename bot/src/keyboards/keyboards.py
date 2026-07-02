from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

# =====================================================================
# 🟥 1. КЛАВИАТУРЫ ДЛЯ ГОСТЯ (НОВИЧКА)
# =====================================================================

def get_guest_main_keyboard() -> InlineKeyboardMarkup:
    """Главное меню для пользователя без подписки"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🚀 Вступить в сообщество", callback_data="buy_subscription")
            ],
            [
                InlineKeyboardButton(text="ℹ️ О сообществе", url="https://www.found-core.com/"),
                InlineKeyboardButton(text="🤝 Отзывы", url="https://www.found-core.com/#reviews")
            ],
            [
                InlineKeyboardButton(text="💼 Мой профиль", callback_data="guest_profile"),
                InlineKeyboardButton(text="❓ Поддержка / FAQ", callback_data="guest_support_faq")
            ],
        ]
    )
    
def get_months_keyboard() -> InlineKeyboardMarkup:
    """Меню выбора количества месяцев подписки"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🥉 1 месяц", callback_data="choose_payment_1")
            ],
            [
                InlineKeyboardButton(text="🥈 2 месяца", callback_data="choose_payment_2")
            ],
            [
                InlineKeyboardButton(text="🥇 3 месяца `-20%`", callback_data="choose_payment_3")
            ],
            [
                InlineKeyboardButton(text="◀️ Назад в меню", callback_data="back_to_guest_main")
            ]
        ]
    )
    
def get_payment_keyboard(months: int) -> InlineKeyboardMarkup:
    """Меню выбора способа оплаты"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💳 Stripe", callback_data=f"stripe_payment_{months}")
            ],
            [
                InlineKeyboardButton(text="💳 Crypto Bot", callback_data=f"crypto_payment_{months}")
            ],
            [
                InlineKeyboardButton(text="◀️ Назад в меню", callback_data="back_to_guest_main")
            ]
        ]
    )

def get_process_payment_keyboard(checkout_url: str) -> InlineKeyboardMarkup:
    """Меню оплаты Stripe (урл генерируется на бэкенде)"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💳 Оплатить доступ", url=checkout_url)
            ],
            [
                InlineKeyboardButton(text="🔄 Проверить оплату", callback_data="verify_payment_status")
            ],
            [
                InlineKeyboardButton(text="◀️ Назад в меню", callback_data="back_to_guest_main")
            ]
        ]
    )

def get_back_to_guest_keyboard() -> InlineKeyboardMarkup:
    """Кнопка возврата для экранов 'О сообществе' и 'Отзывы'"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🚀 Хочу вступить!", callback_data="buy_subscription")
            ],
            [
                InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_guest_main")
            ]
        ]
    )
    
def get_guest_back_keyboard() -> InlineKeyboardMarkup:
    """Кнопка возврата для экрана 'Профиль'"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_guest_main")
            ]
        ]
    )
    
def get_support_keyboard() -> InlineKeyboardMarkup:
    """Кнопка возврата для экрана 'Поддержка / FAQ'"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👨🏻‍💻 Поддержка", callback_data="support")
            ],
            [
                InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_guest_main")
            ]
        ]
    )


# =====================================================================
# 🟩 2. КЛАВИАТУРЫ ДЛЯ РЕЗИДЕНТА (АКТИВНАЯ ПОДПИСКА)
# =====================================================================

def get_resident_main_keyboard() -> InlineKeyboardMarkup:
    """Главное меню для подтвержденного резидента клуба"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✨ Направления", callback_data="destination_list")
            ],
            [
                InlineKeyboardButton(text="💸 Продлить подписку", callback_data="extend_subscription")
            ],
            [
                InlineKeyboardButton(text="ℹ️ О сообществе", url="https://www.found-core.com/"),
                InlineKeyboardButton(text="🤝 Отзывы", url="https://www.found-core.com/#reviews")
            ],
            [
                InlineKeyboardButton(text="💼 Мой профиль", callback_data="resident_profile"),
                InlineKeyboardButton(text="❓ Поддержка / FAQ", callback_data="resident_support_faq")
            ],
        ]
    )
    
def get_destination_list_keyboard(directions: list) -> InlineKeyboardMarkup:
    """Меню направлений"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="🚀 Основное сообщество",
        callback_data=f"main_destination"
    ))
    
    for direction in directions:
        builder.row(InlineKeyboardButton(
            text=direction['name'],
            callback_data=f"direction_go_{direction['telegram_chat_id']}"
        ))
    
    builder.row(InlineKeyboardButton(
        text="◀️ Назад",
        callback_data=f"back_to_resident_main"
    ))
    return builder.as_markup()
    
def get_resident_back_keyboard() -> InlineKeyboardMarkup:
    """Кнопка возврата для экрана 'Профиль'"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_resident_main")
            ]
        ]
    )

def get_extend_process_payment_keyboard(checkout_url: str) -> InlineKeyboardMarkup:
    """Меню оплаты Stripe (урл генерируется на бэкенде)"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💳 Оплатить доступ", url=checkout_url)
            ],
            [
                InlineKeyboardButton(text="◀️ Назад в меню", callback_data="back_to_resident_main")
            ]
        ]
    )
    
def get_extend_payment_keyboard(months: int) -> InlineKeyboardMarkup:
    """Меню выбора способа оплаты"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💳 Stripe", callback_data=f"extend_stripe_payment_{months}")
            ],
            [
                InlineKeyboardButton(text="💳 Crypto Bot", callback_data=f"extend_crypto_payment_{months}")
            ],
            [
                InlineKeyboardButton(text="◀️ Назад в меню", callback_data="back_to_resident_main")
            ]
        ]
    )
    
def get_extend_months_keyboard() -> InlineKeyboardMarkup:
    """Меню выбора количества месяцев продления подписки"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🥉 1 месяц", callback_data="extend_choose_payment_1")
            ],
            [
                InlineKeyboardButton(text="🥈 2 месяца", callback_data="extend_choose_payment_2")
            ],
            [
                InlineKeyboardButton(text="🥇 3 месяца `-20%`", callback_data="extend_choose_payment_3")
            ],
            [
                InlineKeyboardButton(text="◀️ Назад в меню", callback_data="back_to_resident_main")
            ]
        ]
    )
    
# =====================================================================
# 🟨 3. КЛАВИАТУРА ДЛЯ АДМИНИСТРАТОРА
# =====================================================================

def get_admin_main_keyboard() -> InlineKeyboardMarkup:
    """Панель управления для администраторов системы"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👥 Список пользователей", callback_data="admin_get_users")
            ],
            [
                InlineKeyboardButton(text="✨ Список направлений", callback_data="admin_direction_list")
            ],
            [
                InlineKeyboardButton(text="🔑 Найти пользователя", callback_data="admin_find_user")
            ]
        ]
    )


def get_users_list_keyboard(all_users, page: int = 1, limit: int = 10) -> InlineKeyboardMarkup:
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    page_users = all_users[start_idx:end_idx]
    
    builder = InlineKeyboardBuilder()
    
    for user in page_users:
        if user.get('username'):
            button_text = f"👤 @{user['username']}"
        else:
            last_name = f" {user['last_name']}" if user.get('last_name') else ""
            button_text = f"👤 {user['first_name']}{last_name}"
            
        builder.row(InlineKeyboardButton(
            text=button_text, 
            callback_data=f"admin_user_{user['user_id']}_{page}"
        ))
        
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"users_page_{page - 1}"))
    
    if end_idx < len(all_users):
        nav_buttons.append(InlineKeyboardButton(text="Вперед ➡️", callback_data=f"users_page_{page + 1}"))
        
    if nav_buttons:
        builder.row(*nav_buttons)
        
    builder.row(InlineKeyboardButton(
        text="👨🏻‍💻 Главная",
        callback_data="admin_back_to_main"
    ))
        
    return builder.as_markup()

def get_back_to_user_keyboard(user_id: int, page: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="◀️ Назад",
        callback_data=f"admin_user_{user_id}_{page}"
    ))
    return builder.as_markup()

def get_user_levels_keyboard(user_id: int, user_level: int, page: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for i in range(1, 11):
        if i != user_level:
            builder.row(InlineKeyboardButton(
                text=f"🟩 {i}",
                callback_data=f"admin_level_{user_id}_{i}_{page}"
            ))
        else:
            builder.row(InlineKeyboardButton(
                text=f"✅ {i}",     
                callback_data=f"admin_user_{user_id}_{page}"     
            ))
        
    builder.row(InlineKeyboardButton(
        text="◀️ Назад",
        callback_data=f"admin_user_{user_id}_{page}"
    ))
    return builder.as_markup()

def get_direction_list_keyboard(directions: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for direction in directions:
        builder.row(InlineKeyboardButton(
            text=direction['name'],
            callback_data=f"admin_direction_info_{direction['telegram_chat_id']}"
        ))
        
    builder.row(InlineKeyboardButton(
        text="👨🏻‍💻 Главная",
        callback_data="admin_back_to_main"
    ))
    
    return builder.as_markup()

def get_direction_list_access_keyboard(directions: list, user_id: int, page: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for direction in directions:
        builder.row(InlineKeyboardButton(
            text=direction['name'],
            callback_data=f"admin_direction_access_{direction['telegram_chat_id']}_{user_id}_{page}"
        ))
        
    builder.row(InlineKeyboardButton(
        text="◀️ Назад",
        callback_data=f"admin_user_{user_id}_{page}"
    ))
    return builder.as_markup()

def get_direction_card_keyboard(telegram_chat_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="◀️ Назад",
        callback_data=f"admin_direction_info_{telegram_chat_id}"
    ))
    return builder.as_markup()

def get_back_to_admin_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="👨🏻‍💻 Главная",
        callback_data="admin_back_to_main"
    ))
    return builder.as_markup()