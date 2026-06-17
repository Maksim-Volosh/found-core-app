from app.domain.entities import UserEntity
from app.domain.exceptions import (UserNotFoundByTelegramId,
                                   UserNotFoundByUserId, UsersNotFound)
from app.domain.interfaces import IUserRepository


class UserUseCase:
    def __init__(self, repo: IUserRepository) -> None:
        self.repo = repo

    async def get_by_telegram_id(self, telegram_id: int) -> UserEntity:
        user: UserEntity | None = await self.repo.get_by_telegram_id(telegram_id)
        if user is None:
            raise UserNotFoundByTelegramId()
        return user

    async def get_by_user_id(self, user_id: int) -> UserEntity:
        user: UserEntity | None = await self.repo.get_by_user_id(user_id)
        if user is None:
            raise UserNotFoundByUserId()
        return user

    async def get_all(self) -> list[UserEntity]:
        users = await self.repo.get_all()
        if users is None:
            raise UsersNotFound()
        return users