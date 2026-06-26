from aiogram import Dispatcher

from . import start, profile


def register_all_handlers(dp: Dispatcher):
    start.register(dp)
    profile.register(dp)