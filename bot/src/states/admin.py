from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    waiting_for_direction_name = State()
    waiting_for_direction_owner = State()
    waiting_for_direction_screening = State()
    waiting_for_user_username = State()
