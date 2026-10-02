"""Creates a persisted user plus a valid `Authorization` header for protected-route tests."""

import time

import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domain.entities import UserEntity
from app.infrastructure.repositories.user import SqlAlchemyUserRepository
from tests.fixtures.factories import make_new_user_entity


def make_auth_headers(user: UserEntity) -> dict[str, str]:
    now = int(time.time())
    payload = {
        "sub": str(user.id),
        "telegram_id": user.telegram_id,
        "token_version": user.token_version,
        "iat": now,
        "exp": now + 3600,
    }
    token = jwt.encode(payload, settings.auth.secret_key, algorithm=settings.auth.algorithm)
    return {"Authorization": f"Bearer {token}"}


async def create_user_with_headers(
    session: AsyncSession, telegram_id: int, **overrides
) -> tuple[UserEntity, dict[str, str]]:
    user = await SqlAlchemyUserRepository(session).create(
        make_new_user_entity(telegram_id=telegram_id, **overrides)
    )
    # The repository no longer commits; other sessions (HTTP requests) must see the user.
    await session.commit()
    return user, make_auth_headers(user)
