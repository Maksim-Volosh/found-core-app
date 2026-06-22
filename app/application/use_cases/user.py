from app.domain.entities import NewUserEntity, UserEntity
from app.domain.entities.auth_user import AuthUserEntity
from app.domain.entities.subscription import SubscriptionEntity
from app.domain.exceptions import (UserIsBanned, UserNotFoundByTelegramId,
                                   UserNotFoundByUserId, UsersNotFound)
from app.domain.interfaces import IUserRepository, ISubscriptionRepository
from app.domain.mappers.user import map_to_auth_user


class UserUseCase:
    def __init__(self, repo: IUserRepository) -> None:
        self.repo = repo

    async def get_by_user_id(self, user_id: int) -> UserEntity:
        user: UserEntity | None = await self.repo.get_by_user_id(user_id)
        if user is None:
            raise UserNotFoundByUserId()
        return user
    

class UserAuthUseCase:
    def __init__(self, user_repo: IUserRepository, subscription_repo: ISubscriptionRepository) -> None:
        self.user_repo = user_repo
        self.subscription_repo = subscription_repo

    async def auth(self, request_user: NewUserEntity) -> AuthUserEntity:
        user: UserEntity | None = await self.user_repo.get_by_telegram_id(request_user.telegram_id)
        if user is None:
            created_user: UserEntity = await self.user_repo.create_user(request_user)
            return map_to_auth_user(created_user, None)
        if user.is_banned:
            raise UserIsBanned()
        if user.username != request_user.username or user.first_name != request_user.first_name or user.last_name != request_user.last_name:
            # Update user information if it has changed
            user.username = request_user.username
            user.first_name = request_user.first_name
            user.last_name = request_user.last_name
            await self.user_repo.update_user(user)
        subscription: SubscriptionEntity | None = await self.subscription_repo.get_subscription(user.user_id)
        return map_to_auth_user(user, subscription)