from aiogram import Dispatcher

from . import start, profile, back, payment


def register_all_handlers(dp: Dispatcher):
    start.register(dp)
    profile.register(dp)
    back.register(dp)
    payment.register(dp)