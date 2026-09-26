import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.api.v1.dependencies.auth import get_current_user
from app.domain.exceptions import TokenExpiredError, TokenInvalidError, UserBannedError
from tests.fixtures.factories import make_user_entity


class _FakeUseCase:
    def __init__(self, result=None, exc: Exception | None = None) -> None:
        self._result = result
        self._exc = exc

    async def execute(self, token: str):
        if self._exc:
            raise self._exc
        return self._result


class _FakeContainer:
    def __init__(self, use_case: _FakeUseCase) -> None:
        self._use_case = use_case

    def verify_access_token_use_case(self) -> _FakeUseCase:
        return self._use_case


def _credentials(token: str = "irrelevant") -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


async def test_valid_token_returns_user():
    user = make_user_entity(id=1)
    container = _FakeContainer(_FakeUseCase(result=user))

    result = await get_current_user(credentials=_credentials(), container=container)

    assert result is user


async def test_token_invalid_raises_401():
    container = _FakeContainer(_FakeUseCase(exc=TokenInvalidError()))

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=_credentials(), container=container)

    assert exc_info.value.status_code == 401


async def test_token_expired_raises_401():
    container = _FakeContainer(_FakeUseCase(exc=TokenExpiredError()))

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=_credentials(), container=container)

    assert exc_info.value.status_code == 401


async def test_banned_user_raises_403_with_reason():
    container = _FakeContainer(_FakeUseCase(exc=UserBannedError("spam")))

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=_credentials(), container=container)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "spam"


async def test_banned_user_without_reason_falls_back_to_message():
    container = _FakeContainer(_FakeUseCase(exc=UserBannedError(None)))

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=_credentials(), container=container)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "User is banned."
