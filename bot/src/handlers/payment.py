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
router.callback_query.filter(F.message.chat.type == "private")


@router.callback_query(F.data == "buy_subscription")
async def choice_months_for_payment_handler(callback_query: CallbackQuery, backend_user_id: int) -> None:
    if not isinstance(callback_query.message, Message):
        return

    await callback_query.answer()
    user = await container.user_service.get_user_info(backend_user_id)
    print(user)
    if user["screening_status"] == "NOT_STARTED":
        await callback_query.message.edit_text(
            f"Для того что бы вступить в сообщество, необходимо пройти отбор, для этого пожалуйста, напишите @Kateu",
            reply_markup=kb.get_guest_back_keyboard(),
        )
    else:
        await callback_query.message.edit_text(
            f"Для того что бы вступить в сообщество, необходимо оплатить подписку. \nВыберите на сколько месяцев вы хотите оформить подписку.",
            reply_markup=kb.get_months_keyboard(),
        )


@router.callback_query(F.data.startswith("choose_payment_"))
async def choice_payment_method_handler(callback_query: CallbackQuery) -> None:
    if not isinstance(callback_query.message, Message):
        return

    await callback_query.answer()
    data = callback_query.data
    if not data:
        return

    data_parts = data.split("_")
    months = int(data_parts[2])

    await callback_query.message.edit_text(
        f"Отлично, теперь выберите способ оплаты. \nВыберите из доступных в меню ниже.",
        reply_markup=kb.get_payment_keyboard(months),
    )


@router.callback_query(F.data.startswith("stripe_payment_"))
async def stripe_payment_method_handler(
    callback_query: CallbackQuery, backend_user_id: int
) -> None:
    if not isinstance(callback_query.message, Message):
        return
    await callback_query.answer()
    data = callback_query.data
    if not data:
        return

    data_parts = data.split("_")
    months = int(data_parts[2])

    payment = await container.payment_service.create(backend_user_id, months, "STRIPE")

    if payment is None:
        await callback_query.message.edit_text(
            f"✅ Оплата уже совершена. \n\nПодписка активирована.",
            reply_markup=kb.get_resident_main_keyboard(),
        )
        return
    checkout_url = payment["checkout_url"]

    await callback_query.message.edit_text(
        f"Ниже вы можете оплатить подписку с помощью Stripe. \n\nПосле успешной оплаты, пожалуйста, нажмите кнопку проверить оплату и вам будет отправлена ссылка на основное сообщество и вы сможете вступить в него.\n\nЕсли вы сталкнулись с проблемами, пожалуйста, обратитесь к администратору.",
        reply_markup=kb.get_process_payment_keyboard(checkout_url=checkout_url),
    )


@router.callback_query(F.data.startswith("rf_payment_"))
async def rf_payment_method_handler(
    callback_query: CallbackQuery, backend_user_id: int
) -> None:
    if not isinstance(callback_query.message, Message):
        return
    await callback_query.answer()

    await callback_query.message.edit_text(
        f"Мы пока не реализовали возможность оплаты по СНГ картам. \n\nДля того что бы оплатить подписку по СНГ картам, пожалуйста, обратитесь к администратору, вы сможете оплатить переводом. @found_core_admin",
        reply_markup=kb.get_guest_back_keyboard(),
    )


# @router.callback_query(F.data.startswith("crypto_payment_"))
# async def crypto_payment_method_handler(
#     callback_query: CallbackQuery, backend_user_id: int
# ) -> None:
#     if not isinstance(callback_query.message, Message):
#         return
#     await callback_query.answer()
#     data = callback_query.data
#     if not data:
#         return

#     data_parts = data.split("_")
#     months = int(data_parts[2])

#     payment = await container.payment_service.create(backend_user_id, months, "CRYPTO")

#     if payment is None:
#         await callback_query.message.edit_text(
#             f"✅ Оплата уже совершена. \n\nПодписка активирована.",
#             reply_markup=kb.get_resident_main_keyboard(),
#         )
#         return
#     checkout_url = payment["checkout_url"]

#     await callback_query.message.edit_text(
#         f"Ниже вы можете оплатить подписку с помощью Crypto Bot. \n\nПосле успешной оплаты, пожалуйста, нажмите кнопку проверить оплату и вам будет отправлена ссылка на основное сообщество и вы сможете вступить в него.\n\nЕсли вы сталкнулись с проблемами, пожалуйста, обратитесь к администратору.",
#         reply_markup=kb.get_process_payment_keyboard(checkout_url=checkout_url),
#     )


@router.callback_query(F.data == "extend_subscription")
async def extend_choice_months_for_payment_handler(
    callback_query: CallbackQuery,
) -> None:
    if not isinstance(callback_query.message, Message):
        return

    await callback_query.answer()

    await callback_query.message.edit_text(
        f"Выберите на сколько месяцев вы хотите продлить подписку.",
        reply_markup=kb.get_extend_months_keyboard(),
    )


@router.callback_query(F.data.startswith("extend_choose_payment_"))
async def extend_choice_payment_method_handler(callback_query: CallbackQuery) -> None:
    if not isinstance(callback_query.message, Message):
        return

    await callback_query.answer()
    data = callback_query.data
    if not data:
        return

    data_parts = data.split("_")
    months = int(data_parts[3])

    await callback_query.message.edit_text(
        f"Отлично, теперь выберите способ оплаты. \nВыберите из доступных в меню ниже.",
        reply_markup=kb.get_extend_payment_keyboard(months),
    )


@router.callback_query(F.data.startswith("extend_stripe_payment_"))
async def extend_stripe_payment_method_handler(
    callback_query: CallbackQuery, backend_user_id: int
) -> None:
    if not isinstance(callback_query.message, Message):
        return
    await callback_query.answer()
    data = callback_query.data
    if not data:
        return

    data_parts = data.split("_")
    months = int(data_parts[3])

    payment = await container.payment_service.create(backend_user_id, months, "STRIPE")

    if payment is None:
        await callback_query.message.edit_text(
            f"✅ Вам не нужно продлевать подписку.",
            reply_markup=kb.get_resident_main_keyboard(),
        )
        return
    checkout_url = payment["checkout_url"]

    await callback_query.message.edit_text(
        f'Ниже вы можете продлить подписку с помощью Stripe. \n\nПосле успешной оплаты, пожалуйста, перейдите в "главное меню - мой профиль", и проверьте продлена ли подписка. Если вы сталкнулись с проблемами, пожалуйста, обратитесь к администратору.',
        reply_markup=kb.get_extend_process_payment_keyboard(checkout_url=checkout_url),
    )


@router.callback_query(F.data.startswith("extend_rf_payment_"))
async def extend_rf_payment_method_handler(
    callback_query: CallbackQuery, backend_user_id: int
) -> None:
    if not isinstance(callback_query.message, Message):
        return
    await callback_query.answer()

    await callback_query.message.edit_text(
        f"Мы пока не реализовали возможность оплаты по СНГ картам. \n\nДля того что бы оплатить подписку по СНГ картам, пожалуйста, обратитесь к администратору, вы сможете оплатить переводом. @found_core_admin",
        reply_markup=kb.get_resident_back_keyboard(),
    )


# @router.callback_query(F.data.startswith("extend_crypto_payment_"))
# async def extend_crypto_payment_method_handler(
#     callback_query: CallbackQuery, backend_user_id: int
# ) -> None:
#     if not isinstance(callback_query.message, Message):
#         return
#     await callback_query.answer()
#     data = callback_query.data
#     if not data:
#         return

#     data_parts = data.split("_")
#     months = int(data_parts[3])

#     payment = await container.payment_service.create(backend_user_id, months, "CRYPTO")

#     if payment is None:
#         await callback_query.message.edit_text(
#             f"✅ Вам не нужно продлевать подписку.",
#             reply_markup=kb.get_resident_main_keyboard(),
#         )
#         return
#     checkout_url = payment["checkout_url"]

#     await callback_query.message.edit_text(
#         f'Ниже вы можете продлить подписку с помощью Crypto Bot. \n\nПосле успешной оплаты, пожалуйста, перейдите в "главное меню - мой профиль", и проверьте продлена ли подписка. Если вы сталкнулись с проблемами, пожалуйста, обратитесь к администратору.',
#         reply_markup=kb.get_extend_process_payment_keyboard(checkout_url=checkout_url),
#     )


def register(dp: Dispatcher) -> None:
    dp.include_router(router)
