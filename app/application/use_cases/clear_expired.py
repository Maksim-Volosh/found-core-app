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

        expired_subscriptions = await self.subscription_repo.get_expired_subscriptions(now)
        
        if not expired_subscriptions:
            logger.info("Истекших подписок не найдено.")
            return

        logger.info(f"Найдено {len(expired_subscriptions)} истекших подписок. Переводим в EXPIRED...")

        for sub in expired_subscriptions:
            await self.subscription_repo.update_status(sub.subscription_id, SubscriptionStatus.EXPIRED)
            
            # TODO: Сюда в будущем добавишь интеграцию с ботом:
            logger.info(f"Подписка subscription_id:{sub.subscription_id} для пользователя user_id:{sub.user_id} переведена в EXPIRED.")

        await self.subscription_repo.commit()
        logger.info("Фоновая задача успешно завершена.")