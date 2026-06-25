from datetime import datetime, timezone
import logging

from app.domain.interfaces import ISubscriptionRepository
from app.domain.entities.subscription import SubscriptionStatus

logger = logging.getLogger(__name__)

class ClearExpiredSubscriptionsUseCase:
    def __init__(self, subscription_repo: ISubscriptionRepository):
        self.subscription_repo = subscription_repo

    async def execute(self) -> None:
        logger.info("Запуск фоновой задачи проверки истекших подписок...")
        
        now = datetime.now(timezone.utc)
        
        # 1. Запрашиваем из репозитория подписки, у которых статус ACTIVE, но время истекло.
        # Твой метод репозитория должен вернуть список таких подписок.
        expired_subscriptions = await self.subscription_repo.get_expired_subscriptions(now)
        
        if not expired_subscriptions:
            logger.info("Истекших подписок не найдено.")
            return

        logger.info(f"Найдено {len(expired_subscriptions)} истекших подписок. Переводим в EXPIRED...")

        for sub in expired_subscriptions:
            # 2. Меняем статус в памяти сессии
            await self.subscription_repo.update_status(sub.subscription_id, SubscriptionStatus.EXPIRED)
            
            # TODO: Сюда в будущем добавишь интеграцию с ботом:
            # await self.bot_service.kick_user(user_id=sub.user_id, chat_id=...)
            logger.info(f"Подписка {sub.subscription_id} для пользователя {sub.user_id} переведена в EXPIRED.")

        # 3. Коммитим все изменения одной транзакцией
        await self.subscription_repo.commit()
        logger.info("Фоновая задача успешно завершена.")