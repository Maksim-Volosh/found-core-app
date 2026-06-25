from app.domain.entities import UserEntity
from app.domain.exceptions import (InvalidUserLevel, UserNotFoundByUserId,
                                   UsersNotFound)
from app.domain.interfaces import IUserRepository


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