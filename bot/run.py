import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from config import TOKEN
from src.handlers import register_all_handlers
from src.http.http_client import http

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


async def on_startup():
    await http.start()
    register_all_handlers(dp)

async def on_shutdown():
    await http.close()
    
    
async def main() -> None:
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    await dp.start_polling(
        bot,
        allowed_updates=["message", "callback_query", "chat_member"]
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())