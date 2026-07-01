from datetime import datetime, timedelta, timezone

import src.keyboards.keyboards as kb
from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters.chat_member_updated import (JOIN_TRANSITION,
                                                 ChatMemberUpdatedFilter)
from aiogram.types import CallbackQuery, ChatMemberUpdated, Message
from config import MAIN_CHAT_ID
from src.container import container

router = Router()
router.message.filter(F.chat.type == "private")
router.callback_query.filter(F.message.chat.type == "private")

@router.callback_query(F.data == "verify_payment_status")
async def verify_payment_status_handler(callback_query: CallbackQuery, backend_user_id: int, bot: Bot) -> None:
    if not isinstance(callback_query.message, Message):
        return
    
    await callback_query.answer()
    access_data = await container.access_service.check_main_access(backend_user_id)
    
    if access_data and access_data["allowed"]:
        try:
            await bot.unban_chat_member(chat_id=MAIN_CHAT_ID, user_id=callback_query.from_user.id)
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
    
@router.callback_query(F.data == "destination_list")
async def main_destination_handler(callback_query: CallbackQuery) -> None:
    if not isinstance(callback_query.message, Message):
        return

    await callback_query.answer()
    directions = await container.direction_service.get_directions()
    
    await callback_query.message.edit_text(
        f"Список доступных направлений:",
        reply_markup=kb.get_destination_list_keyboard(directions)
    )
    
@router.callback_query(F.data == "main_destination")
async def destination_list_handler(callback_query: CallbackQuery, backend_user_id: int, bot: Bot) -> None:
    if not isinstance(callback_query.message, Message):
        return

    await callback_query.answer()
    access_data = await container.access_service.check_main_access(backend_user_id)
    
    if access_data and access_data["allowed"]:
        try:
            if await is_user_in_chat(bot, MAIN_CHAT_ID, callback_query.from_user.id):
                await callback_query.message.edit_text(
                    f"✅ Вы уже вступили в основное сообщество.",
                    reply_markup=kb.get_resident_main_keyboard()
                )
                return
            
            await bot.unban_chat_member(chat_id=MAIN_CHAT_ID, user_id=callback_query.from_user.id)
            invite_link_object = await bot.create_chat_invite_link(
                chat_id=MAIN_CHAT_ID,
                member_limit=1, 
                expire_date=datetime.now(timezone.utc) + timedelta(minutes=5),
                name=f"User {backend_user_id} Access Link"
            )
        
            access_link = invite_link_object.invite_link
            
            await callback_query.message.edit_text(
                f"✅ Для вступления в основное сообщество вам необходимо перейти по ссылке: {access_link} \n\n‼️‼️ Ссылка действительна 5 минут!",
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
        f"❌ У вас нет доступа. \n\nПожалуйста, оплатите подписку, чтобы вступить в основное сообщество. При возникновении ошибок обратитесь к администратору.",
        reply_markup=kb.get_payment_keyboard()
    )
    
@router.callback_query(F.data.startswith("direction_go_"))
async def direction_go_handler(callback_query: CallbackQuery, backend_user_id: int, bot: Bot) -> None:
    if not isinstance(callback_query.message, Message):
        return

    await callback_query.answer()
    
    access_data = await container.access_service.check_main_access(backend_user_id)
    
    if access_data and access_data["allowed"]:
        try:
            data = callback_query.data
            if not data:
                return
            
            data_parts = data.split("_")
            telegram_chat_id = int(data_parts[2])
            
            direction_response = await container.direction_service.get_direction(telegram_chat_id)
            if not direction_response: return
            
            if direction_response["requires_screening"] is True:
                direction_access_response = await container.direction_service.get_direction_access(backend_user_id, telegram_chat_id)  
                if direction_access_response is None:
                    created_direction_access =  await container.direction_service.create_direction_access(backend_user_id, telegram_chat_id)
                    direction_access = created_direction_access["screening_status"]
                else:
                    direction_access = direction_access_response["screening_status"]
                    
                if direction_access == "NOT_STARTED":
                    owner_username = direction_response["owner_username"]
                    await callback_query.message.edit_text(
                        f"❌ У вас нет доступа к данному направлению так как вы не прошли скрининг. \n\nДля прохождения скрининга напишите владельцу направления: @{owner_username}",
                        reply_markup=kb.get_resident_main_keyboard()
                    )
                    return
            
            if await is_user_in_chat(bot, telegram_chat_id, callback_query.from_user.id):
                await callback_query.message.edit_text(
                    f"✅ Вы уже вступили в данное сообщество.",
                    reply_markup=kb.get_resident_main_keyboard()
                )
                return
            
            await bot.unban_chat_member(chat_id=telegram_chat_id, user_id=callback_query.from_user.id)
            invite_link_object = await bot.create_chat_invite_link(
                chat_id=telegram_chat_id,
                member_limit=1, 
                expire_date=datetime.now(timezone.utc) + timedelta(minutes=5),
                name=f"User {backend_user_id} Access Link"
            )
        
            access_link = invite_link_object.invite_link
            
            await callback_query.message.edit_text(
                f"✅ Отлично, вы получили доступ к направлению! \nДля вступления в сообщество вам необходимо перейти по ссылке: {access_link} \n\n‼️‼️ Ссылка действительна 5 минут!",
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
        f"❌ У вас нет доступа. \n\nПожалуйста, оплатите подписку, чтобы вступить в сообщество. При возникновении ошибок обратитесь к администратору.",
        reply_markup=kb.get_payment_keyboard()
    )
    
async def is_user_in_chat(bot: Bot, chat_id: int, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        
        if member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]:
            return True
            
        return False

    except TelegramBadRequest as e:
        if "user not found" in str(e).lower():
            return False
        
        print(f"Ошибка проверки пользователя в чате: {e}")
        return False
    
@router.chat_member(ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION))
async def on_user_join(event: ChatMemberUpdated, bot: Bot):
    chat_id = event.chat.id
    user = event.new_chat_member.user
    auth_data = {
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name
    }
    try:
        user_data = await container.auth_service.auth(auth_data, user.id)
        backend_user_id = user_data.get("user_id")
    
        if not backend_user_id:
            is_allowed = False
        else:
            is_allowed_data = await container.access_service.check_main_access(backend_user_id)
            is_allowed = is_allowed_data["allowed"]            
    except Exception:
        is_allowed = False
        
    if is_allowed is False:
        await bot.ban_chat_member(chat_id=chat_id, user_id=user.id)
                            
        await bot.send_message(
            chat_id=user.id, 
            text="❌ Вы были удалены из группы, так как у вас нет активной подписки. Оплатите её в боте."
        )
    else:
        await bot.send_message(
            chat_id=chat_id,
            text=f"Добро пожаловать в наше сообщество, {user.mention_markdown()}! 🎉",
            parse_mode="Markdown"
        )
    
def register(dp: Dispatcher) -> None:
    dp.include_router(router)