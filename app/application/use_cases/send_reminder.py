import logging
from datetime import datetime, timedelta, timezone

from app.domain.interfaces import (IBotService, ISubscriptionRepository,
                                   IUserRepository)

logger = logging.getLogger(__name__)

class SendSubscriptionRemindersUseCase:
    def __init__(self, subscription_repo: ISubscriptionRepository, user_repo: IUserRepository, bot_service: IBotService):
        self.subscription_repo = subscription_repo
        self.user_repo = user_repo
        self.bot_service = bot_service

    async def execute(self) -> None:
        logger.info("Запуск проверки необходимости отправки напоминаний...")
        now = datetime.now(timezone.utc)

        target_7_days = now + timedelta(days=7)
        subs_7 = await self.subscription_repo.get_subs_for_7_days_reminder(target_7_days)
        
        for sub in subs_7:
            user = await self.user_repo.get_by_user_id(sub.user_id)
            if user:
                success = await self.bot_service.send_message(
                    telegram_id=user.telegram_id,
                    text="⚠️ Напоминание: До окончания вашей подписки осталось менее 7 дней! Продлите её, чтобы не потерять доступ."
                )
                if success:
                    sub.reminded_7_days = True 
        logger.info(f"Отправлено напоминаний для {len(subs_7)} подписок, срок действия которых истекает через <= 7 дней.")        
        
        target_3_days = now + timedelta(days=3)
        subs_3 = await self.subscription_repo.get_subs_for_3_days_reminder(target_3_days)
        
        for sub in subs_3:
            user = await self.user_repo.get_by_user_id(sub.user_id)
            if user:
                success = await self.bot_service.send_message(
                    telegram_id=user.telegram_id,
                    text="🚨 Внимание: До окончания вашей подписки осталось всего 3 дня! Скоро доступы будут заблокированы."
                )
                if success:
                    sub.reminded_3_days = True
        logger.info(f"Отправлено напоминаний для {len(subs_3)} подписок, срок действия которых истекает через <= 3 дней.")        

        for sub in subs_7 + subs_3:
            await self.subscription_repo.update_subscription(sub)
        await self.subscription_repo.commit()
        await self.bot_service.close()
        logger.info("Фоновая задача напоминаний завершена.")