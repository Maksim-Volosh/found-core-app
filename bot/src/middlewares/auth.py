from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from src.container import container

class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        state = data.get("state")
        
        backend_user_id = None
        if state:
            state_data = await state.get_data()
            backend_user_id = state_data.get("backend_user_id")

        if not backend_user_id and isinstance(event, (Message, CallbackQuery)):
            user = event.from_user
            if user:
                auth_data = {
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name
                }

                try:
                    user_data = await container.auth_service.auth(auth_data, user.id)
                    backend_user_id = user_data["user_id"]
                    
                    if state:
                        await state.update_data(backend_user_id=backend_user_id)
                except Exception:
                    pass

        data["backend_user_id"] = backend_user_id

        return await handler(event, data)