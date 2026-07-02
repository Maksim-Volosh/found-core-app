import logging
from datetime import datetime, timezone

from app.core.config import settings
from app.domain.entities.subscription import SubscriptionStatus
from app.domain.interfaces import (IBotService, IDirectionRepository,
                                   ISubscriptionRepository, IUserRepository)

logger = logging.getLogger(__name__)

class ClearExpiredSubscriptionsUseCase:
    def __init__(self, subscription_repo: ISubscriptionRepository, direction_repo: IDirectionRepository, user_repo: IUserRepository, bot_service: IBotService):
        self.subscription_repo = subscription_repo
        self.direction_repo = direction_repo
        self.user_repo = user_repo
        self.bot_service = bot_service

    async def execute(self) -> None:
        logger.info("Запуск фоновой задачи проверки истекших подписок...")
        
        now = datetime.now(timezone.utc)

        expired_subscriptions = await self.subscription_repo.get_expired_subscriptions(now)
        
        if not expired_subscriptions:
            logger.info("Истекших подписок не найдено.")
            return

        logger.info(f"Найдено {len(expired_subscriptions)} истекших подписок. Переводим в EXPIRED...")

        directions = await self.direction_repo.get_directions()
        
        for sub in expired_subscriptions:
            user = await self.user_repo.get_by_user_id(sub.user_id)
            if user is None:
                logger.info(f"Пользователь {sub.user_id} не найден. Удаление пользователя из направлений не требуется.")
                continue
            
            main_result = await self.bot_service.ban_user(
                telegram_id=user.telegram_id,
                chat_id=settings.telegram.main_chat_id
            )
            if main_result:
                logger.info(f"Пользователь {sub.user_id} удален из основного чата с id:{settings.telegram.main_chat_id}")
            else:
                logger.error(f"Не удалось удалить пользователя {sub.user_id} из основного чата с id:{settings.telegram.main_chat_id}")
            
            directions_len_banned = 0
            directions_result = False
            if directions:
                for direction in directions:
                    res = await self.bot_service.ban_user(
                        telegram_id=user.telegram_id,
                        chat_id=direction.telegram_chat_id
                    )
                    if res:
                        directions_len_banned += 1
                    logger.info(f"Пользователь {sub.user_id} удален из чата {direction.name} c id:{direction.telegram_chat_id}")
                if len(directions) == directions_len_banned:
                    directions_result = True
            else:
                logger.info("Направлений не найдено. Удаление пользователя из направлений не требуется.")
                directions_result = True
                    
            if main_result and directions_result:
                await self.subscription_repo.update_status(sub.subscription_id, SubscriptionStatus.EXPIRED)
                await self.bot_service.send_message(
                    telegram_id=user.telegram_id,
                    text=f"Ваша подписка истекла! Нам пришлось удалить ваш доступ к сообществу. Чтобы продолжить пользоваться сервисом, пожалуйста, продлите подписку."
                )
                logger.info(f"Подписка subscription_id:{sub.subscription_id} для пользователя user_id:{sub.user_id} переведена в EXPIRED.")
            else:
                logger.error(f"Не удалось удалить пользователя user_id:{sub.user_id} из всех чатов. Подписка subscription_id:{sub.subscription_id} не переведена в EXPIRED.")
        
        await self.subscription_repo.commit()
        await self.bot_service.close()
        logger.info("Фоновая задача успешно завершена.")