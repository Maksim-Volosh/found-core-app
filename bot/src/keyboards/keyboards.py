from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


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
                InlineKeyboardButton(text="❓ Поддержка / FAQ", callback_data="support_faq")
            ],
        ]
    )
    
def get_payment_keyboard() -> InlineKeyboardMarkup:
    """Меню выбора способа оплаты"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💳 Stripe", callback_data="stripe_payment")
            ],
            [
                InlineKeyboardButton(text="💳 Crypto Bot", callback_data="crypto_payment")
            ],
            [
                InlineKeyboardButton(text="◀️ Назад в меню", callback_data="back_to_guest_main")
            ]
        ]
    )


def get_stripe_payment_keyboard(checkout_url: str) -> InlineKeyboardMarkup:
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
                InlineKeyboardButton(text="ℹ️ О сообществе", url="https://www.found-core.com/"),
                InlineKeyboardButton(text="🤝 Отзывы", url="https://www.found-core.com/#reviews")
            ],
            [
                InlineKeyboardButton(text="💼 Мой профиль", callback_data="resident_profile"),
                InlineKeyboardButton(text="❓ Поддержка / FAQ", callback_data="support_faq")
            ],
        ]
    )
    
def get_destination_list_keyboard() -> InlineKeyboardMarkup:
    """Меню направлений"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🚀 Основное сообщество", callback_data="main_destination")
            ],
            [
                InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_resident_main")
            ],
        ]
    )
    
def get_resident_back_keyboard() -> InlineKeyboardMarkup:
    """Кнопка возврата для экрана 'Профиль'"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_resident_main")
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
                InlineKeyboardButton(text="📊 Статистика", callback_data="admin_get_stats")
            ],
            [
                InlineKeyboardButton(text="📢 Создать рассылку", callback_data="admin_start_broadcast")
            ],
            [
                InlineKeyboardButton(text="🔑 Найти пользователя", callback_data="admin_find_user")
            ]
        ]
    )