from aiogram import Dispatcher

from . import start, profile, back, payment, access, admin, create_direction


def register_all_handlers(dp: Dispatcher):
    start.register(dp)
    profile.register(dp)
    back.register(dp)
    payment.register(dp)
    access.register(dp)
    admin.register(dp)
    create_direction.register(dp)