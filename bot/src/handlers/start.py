from datetime import datetime

from aiogram import Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.filters.chat_member_updated import ChatMemberUpdatedFilter, JOIN_TRANSITION
from aiogram.types import ChatMemberUpdated
from src.container import container
import src.keyboards.keyboards as kb

router = Router()

@router.message(CommandStart(), F.chat.type == "private")
async def command_start_handler(message: Message) -> None:
    if message.from_user:
        auth_service = container.auth_service
        data = {
            "username": message.from_user.username,
            "first_name": message.from_user.first_name,
            "last_name": message.from_user.last_name
        }

        user_data = await auth_service.auth(data, message.from_user.id)
        
        if user_data is None:
            await message.answer(
                "❌ Вы были заблокированы в данном сообществе. \n\nПожалуйста, обратитесь к администратору для получения дополнительной информации.",
                reply_markup=None
            )
            return
        
        if not user_data["subscription"]:
            await message.answer(
                f"Привет, {user_data["first_name"]}!", 
                reply_markup=kb.get_guest_main_keyboard()
            )
        elif user_data["is_admin"]:
            await message.answer(
                f"Привет, {user_data['first_name']}!", 
                reply_markup=kb.get_admin_main_keyboard()
            )
        else:
            await message.answer(
                f"Привет, {user_data["first_name"]}!",
                reply_markup=kb.get_resident_main_keyboard()
            )



def register(dp: Dispatcher) -> None:
    dp.include_router(router)