import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.infrastructure.helpers.db import db_helper
from app.core.composition.container import Container

logger = logging.getLogger(__name__)

async def check_subscriptions_job():
    async for session in db_helper.session_getter():
        try:
            container = Container(session=session)
            # 1. Задача очистки просроченных
            clear_use_case = container.get_clear_expired_subscriptions_use_case()
            await clear_use_case.execute()
            
            # 2. Задача напоминаний
            reminder_use_case = container.get_send_subscription_reminders_use_case()
            await reminder_use_case.execute()
        except Exception as e:
            logger.error(f"Ошибка при выполнении фоновой задачи очистки подписок: {e}", exc_info=True)
        break

def start_scheduler():
    scheduler = AsyncIOScheduler()
    
    scheduler.add_job(
        check_subscriptions_job, 
        "interval", 
        hours=6,
        id="check_subscriptions_expired",
        replace_existing=True
    )
    
    scheduler.start()
    return scheduler