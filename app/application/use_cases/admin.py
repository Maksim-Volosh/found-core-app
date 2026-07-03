from datetime import datetime, timedelta, timezone

from app.domain.entities import SubscriptionEntity, UserEntity
from app.domain.entities.subscription import SubscriptionStatus
from app.domain.exceptions import (InvalidPaymentMonths, InvalidUserLevel,
                                   UserNotFoundByUserId, UsersNotFound)
from app.domain.interfaces import ISubscriptionRepository, IUserRepository


class AdminUseCase:
    def __init__(self, user_repo: IUserRepository) -> None:
        self.user_repo = user_repo

    async def get_users(self) -> list[UserEntity]:
        users = await self.user_repo.get_users()
        if users is None:
            raise UsersNotFound()
        return users

    async def change_user_level(self, user_id: int, level: int) -> UserEntity:
        if level < 1 or level > 10:
            raise InvalidUserLevel()
        user = await self.user_repo.change_user_level(user_id, level)
        if user is None:
            raise UserNotFoundByUserId()
        return user
    
    async def ban_user(self, user_id: int, decision: bool) -> UserEntity:
        user = await self.user_repo.ban_user(user_id, decision)
        if user is None:
            raise UserNotFoundByUserId()
        return user
    
    async def set_admin(self, user_id: int, decision: bool) -> UserEntity:
        user = await self.user_repo.set_admin(user_id, decision)
        if user is None:
            raise UserNotFoundByUserId()
        return user
    
class AdminSubscriptionUseCase:
    def __init__(self, user_repo: IUserRepository, subscription_repo: ISubscriptionRepository) -> None:
        self.user_repo = user_repo
        self.subscription_repo = subscription_repo

    async def give_subscription(self, user_id: int, months: int) -> SubscriptionEntity:
        if months <= 0 or months > 12:
            raise InvalidPaymentMonths()
        user = await self.user_repo.get_by_user_id(user_id)
        if user is None:
            raise UserNotFoundByUserId()
        
        subscription = await self.subscription_repo.get_subscription(user_id)
        if subscription and subscription.status == SubscriptionStatus.ACTIVE:
            subscription.expires_at = subscription.expires_at + (timedelta(days=30) * months)
            subscription.reminded_3_days = False
            subscription.reminded_7_days = False
            await self.subscription_repo.update_subscription(subscription)
            await self.subscription_repo.commit()
            return subscription
        
        now_utc = datetime.now(timezone.utc)
        expires_at = now_utc + (timedelta(days=30) * months)
        new_subscription = SubscriptionEntity(
            subscription_id=0,
            user_id=user_id,
            started_at=now_utc,
            expires_at=expires_at,
            status=SubscriptionStatus.ACTIVE,
            reminded_3_days=False,
            reminded_7_days=False
        )
        await self.subscription_repo.create_subscription(new_subscription)

        await self.subscription_repo.commit()
        
        return new_subscription