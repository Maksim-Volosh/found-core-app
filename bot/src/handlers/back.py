
from aiogram import Dispatcher, F, Router
from aiogram.types import CallbackQuery, Message
import src.keyboards.keyboards as kb

router = Router()
router.message.filter(F.chat.type == "private")

@router.callback_query(F.data == "back_to_guest_main")
async def back_to_guest_main(callback_query: CallbackQuery) -> None:
    if not isinstance(callback_query.message, Message):
        return
    
    await callback_query.answer()
    
    await callback_query.message.edit_text(
        f"⚜️ Главное меню \n\nВыберите действие из доступных в меню ниже.",
        reply_markup=kb.get_guest_main_keyboard()
    )
    
@router.callback_query(F.data == "back_to_resident_main")
async def back_to_resident_main(callback_query: CallbackQuery) -> None:
    if not isinstance(callback_query.message, Message):
        return
    
    await callback_query.answer()
    
    await callback_query.message.edit_text(
        f"⚜️ Главное меню \n\nВыберите действие из доступных в меню ниже.",
        reply_markup=kb.get_resident_main_keyboard()
    )
    
    
def register(dp: Dispatcher) -> None:
    dp.include_router(router)