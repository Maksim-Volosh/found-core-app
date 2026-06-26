from datetime import datetime, timedelta, timezone
from typing import Any

import src.keyboards.keyboards as kb
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.filters.chat_member_updated import (JOIN_TRANSITION,
                                                 ChatMemberUpdatedFilter)
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, ChatMemberUpdated, Message
from config import MAIN_CHAT_ID
from src.container import container

router = Router()
router.message.filter(F.chat.type == "private")

@router.callback_query(F.data == "verify_payment_status")
async def verify_payment_status_handler(callback_query: CallbackQuery, backend_user_id: int, bot: Bot) -> None:
    if not isinstance(callback_query.message, Message):
        return
    
    await callback_query.answer()
    access_data = await container.access_service.check_main_access(backend_user_id)
    
    if access_data and access_data["allowed"]:
        try:
            invite_link_object = await bot.create_chat_invite_link(
                chat_id=MAIN_CHAT_ID,
                member_limit=1, 
                expire_date=datetime.now(timezone.utc) + timedelta(minutes=30),
                name=f"User {backend_user_id} Access Link"
            )
        
            access_link = invite_link_object.invite_link
            
            await callback_query.message.edit_text(
                f"✅ Оплата совершена успешно. \n\nПодписка активирована. Вот ссылка на основное сообщество: {access_link} \n\n‼️‼️ Ссылка действительна 30 минут!",
                reply_markup=kb.get_resident_main_keyboard()
            )
            return
        
        except Exception as e:
            await callback_query.message.answer(
                "⚠️ Произошла ошибка при генерации ссылки. Убедитесь, что бот является администратором группы "
                "и имеет права на создание пригласительных ссылок."
            )
        return
    
    await callback_query.message.edit_text(
        f"❌ Оплата не совершена. \n\nПожалуйста, оплатите подписку, чтобы вступить в основное сообщество. При возникновении ошибок обратитесь к администратору.",
        reply_markup=kb.get_payment_keyboard()
    )
    
def register(dp: Dispatcher) -> None:
    dp.include_router(router)