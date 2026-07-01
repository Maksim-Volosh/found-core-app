from aiogram import Dispatcher

from . import admin_create_direction, start, profile, back, payment, access, admin


def register_all_handlers(dp: Dispatcher):
    start.register(dp)
    profile.register(dp)
    back.register(dp)
    payment.register(dp)
    access.register(dp)
    admin.register(dp)
    admin_create_direction.register(dp)