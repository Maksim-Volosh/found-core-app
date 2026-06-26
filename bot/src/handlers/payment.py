from datetime import datetime
from typing import Any

from aiogram import Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.filters.chat_member_updated import ChatMemberUpdatedFilter, JOIN_TRANSITION
from aiogram.types import ChatMemberUpdated
from src.container import container
import src.keyboards.keyboards as kb

router = Router()
router.message.filter(F.chat.type == "private")

@router.callback_query(F.data == "buy_subscription")
async def choice_payment_method(callback_query: CallbackQuery) -> None:
    if not isinstance(callback_query.message, Message):
        return
    
    await callback_query.answer()
    
    await callback_query.message.edit_text(
        f"Для того что бы вступить в сообщество, необходимо оплатить подписку. \nВыберите способ оплаты из доступных вариантов в меню ниже.",
        reply_markup=kb.get_payment_keyboard()
    )
    
@router.callback_query(F.data == "stripe_payment")
async def stripe_payment_method(callback_query: CallbackQuery, backend_user_id: int) -> None:
    if not isinstance(callback_query.message, Message):
        return
    await callback_query.answer()
    
    payment = await container.payment_service.create(backend_user_id, "STRIPE")
    
    if payment is None:
        await callback_query.message.edit_text(
            f"✅ Оплата уже совершена. \n\nПодписка активирована.",
            reply_markup=kb.get_resident_main_keyboard()
        )
        return
    checkout_url = payment["checkout_url"]
    
    await callback_query.message.edit_text(
        f"Ниже вы можете оплатить подписку с помощью Stripe. \n\nПосле успешной оплаты вам будет отправлена ссылка на основное сообщество и вы сможете вступить в него. Если ссылка не пришла, пожалуйста, нажмите кнопку проверить оплату.",
        reply_markup=kb.get_stripe_payment_keyboard(checkout_url=checkout_url)
    )
        

def register(dp: Dispatcher) -> None:
    dp.include_router(router)