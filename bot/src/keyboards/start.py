from aiogram.filters.callback_data import CallbackData
from aiogram.types import (InlineKeyboardMarkup, KeyboardButton, Message,
                           ReplyKeyboardMarkup)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Мой профиль"), KeyboardButton(text="Доступ")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)

main_kb_without_subscription = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Мой профиль"), KeyboardButton(text="Подписка")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)