from aiogram import Dispatcher

from . import (
    access,
    admin,
    admin_create_direction,
    back,
    payment,
    profile,
    start,
    support,
)


def register_all_handlers(dp: Dispatcher):
    start.register(dp)
    profile.register(dp)
    back.register(dp)
    payment.register(dp)
    access.register(dp)
    admin.register(dp)
    admin_create_direction.register(dp)
    support.register(dp)
