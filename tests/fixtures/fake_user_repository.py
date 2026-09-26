from app.domain.entities import NewUserEntity, UserEntity
from app.domain.interfaces import IUserRepository


class FakeUserRepository(IUserRepository):
    """In-memory stand-in for SqlAlchemyUserRepository, used to unit-test use
    cases without a database. Implements the real IUserRepository ABC so a
    signature drift there fails these tests too."""

    def __init__(self, users: list[UserEntity] | None = None) -> None:
        self._users: dict[int, UserEntity] = {u.id: u for u in (users or [])}
        self._next_id = max(self._users, default=0) + 1

    async def get_by_telegram_id(self, telegram_id: int) -> UserEntity | None:
        for user in self._users.values():
            if user.telegram_id == telegram_id:
                return user
        return None

    async def get_by_id(self, user_id: int) -> UserEntity | None:
        return self._users.get(user_id)

    async def create(self, user: NewUserEntity) -> UserEntity:
        entity = UserEntity(
            id=self._next_id,
            telegram_id=user.telegram_id,
            first_name=user.first_name,
            created_at=user.created_at,
            last_active_at=user.last_active_at,
            last_name=user.last_name,
            username=user.username,
            photo_url=user.photo_url,
            language_code=user.language_code,
        )
        self._users[entity.id] = entity
        self._next_id += 1
        return entity

    async def update(self, user: UserEntity) -> UserEntity:
        self._users[user.id] = user
        return user
