"""Exercises `get_current_user` over real HTTP.

No production route uses this dependency yet (stage 2 only builds it, per
CLAUDE.md), so this mounts a single test-only protected route on a throwaway
FastAPI app -- not `app.main.main_app` -- purely to drive the real dependency
chain (HTTPBearer -> get_current_user -> get_container -> db_helper) over
actual HTTP headers.

Note: the installed FastAPI's `HTTPBearer` raises 401 (not the older/common
403) for a missing or malformed `Authorization` header -- see
`HTTPBase.make_not_authenticated_error`. So every failure mode here except
"banned" (403, from `get_current_user`'s own exception mapping) converges
on 401.
"""

import time

import jwt
import pytest_asyncio
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1.dependencies.auth import get_current_user
from app.core.config import settings
from app.domain.entities import UserEntity
from app.infrastructure.repositories.user import SqlAlchemyUserRepository
from tests.fixtures.db_ops import bump_token_version, set_user_banned
from tests.fixtures.factories import make_new_user_entity

_test_app = FastAPI()


@_test_app.get("/_test/protected")
async def _protected(current_user: UserEntity = Depends(get_current_user)) -> dict:
    return {"user_id": current_user.id}


@pytest_asyncio.fixture
async def protected_client():
    transport = ASGITransport(app=_test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def _create_user(session, **overrides):
    repo = SqlAlchemyUserRepository(session)
    return await repo.create(make_new_user_entity(**overrides))


def _token_for(
    user_id: int,
    telegram_id: int,
    token_version: int = 0,
    is_admin: bool = False,
    expired: bool = False,
) -> str:
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "telegram_id": telegram_id,
        "token_version": token_version,
        "is_admin": is_admin,
        "iat": now - 3600 if expired else now,
        "exp": now - 1 if expired else now + 3600,
    }
    return jwt.encode(payload, settings.auth.secret_key, algorithm=settings.auth.algorithm)


async def test_missing_authorization_header_returns_401(protected_client):
    response = await protected_client.get("/_test/protected")
    assert response.status_code == 401


async def test_malformed_authorization_header_returns_401(protected_client):
    response = await protected_client.get("/_test/protected", headers={"Authorization": "NotBearer xyz"})
    assert response.status_code == 401


async def test_valid_token_returns_200_with_user_id(protected_client, session):
    user = await _create_user(session, telegram_id=800001)
    token = _token_for(user.id, user.telegram_id)

    response = await protected_client.get("/_test/protected", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["user_id"] == user.id


async def test_expired_token_returns_401(protected_client, session):
    user = await _create_user(session, telegram_id=800002)
    token = _token_for(user.id, user.telegram_id, expired=True)

    response = await protected_client.get("/_test/protected", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


async def test_garbage_token_returns_401(protected_client):
    response = await protected_client.get("/_test/protected", headers={"Authorization": "Bearer garbage"})
    assert response.status_code == 401


async def test_banned_after_token_issued_returns_403(protected_client, session):
    user = await _create_user(session, telegram_id=800003)
    token = _token_for(user.id, user.telegram_id)

    await set_user_banned(session, user.id, "abuse")

    response = await protected_client.get("/_test/protected", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403
    assert response.json()["detail"] == "abuse"


async def test_token_version_bumped_after_issue_returns_401(protected_client, session):
    user = await _create_user(session, telegram_id=800004)
    token = _token_for(user.id, user.telegram_id, token_version=0)

    await bump_token_version(session, user.id, 1)

    response = await protected_client.get("/_test/protected", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
