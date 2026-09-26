"""Direct DB mutation helpers for integration tests.

Bypass the repository on purpose: `SqlAlchemyUserRepository.update()` (via
`apply_user_entity_to_user_model`) intentionally never touches `is_banned`,
`ban_reason`, or `token_version` -- there is no ban/logout endpoint yet
(that's stage 8 work), so these fields can only be set directly against the
DB for test setup.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def set_user_banned(session: AsyncSession, user_id: int, ban_reason: str | None) -> None:
    await session.execute(
        text("UPDATE users SET is_banned = true, ban_reason = :reason WHERE id = :id"),
        {"reason": ban_reason, "id": user_id},
    )
    await session.commit()


async def bump_token_version(session: AsyncSession, user_id: int, new_version: int) -> None:
    await session.execute(
        text("UPDATE users SET token_version = :v WHERE id = :id"),
        {"v": new_version, "id": user_id},
    )
    await session.commit()
