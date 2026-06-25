import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.infrastructure.helpers.db import db_helper
from app.core.composition.container import Container

logger = logging.getLogger(__name__)

async def check_subscriptions_job():
    """Сама обертка таски, которая создает изолированную сессию БД"""
    # Используем твой генератор сессий db_helper.session_getter
    async for session in db_helper.session_getter():
        try:
            # Собираем контейнер специально для этой сессии
            container = Container(session=session)
            
            # Нам нужен Use Case (добавь его фабрику в свой Container, если еще не сделал)
            # Допустим, ты назовешь его clear_expired_subscriptions_use_case
            use_case = container.get_clear_expired_subscriptions_use_case()
            
            # Выполняем бизнес-логику
            await use_case.execute()
        except Exception as e:
            logger.error(f"Ошибка при выполнении фоновой задачи очистки подписок: {e}", exc_info=True)
        break # Выходим из генератора после одной итерации

def start_scheduler():
    scheduler = AsyncIOScheduler()
    
    # Добавляем задачу: запускать каждые 6 часов
    # Для тестов можешь поставить: seconds=10 или minutes=1
    scheduler.add_job(
        check_subscriptions_job, 
        "interval", 
        hours=10,
        id="check_subscriptions_expired",
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("APScheduler успешно запущен и запланирован на каждые 6 часов.")
    return scheduler