from aiogram import Dispatcher

from . import start


def register_all_handlers(dp: Dispatcher):
    start.register(dp)