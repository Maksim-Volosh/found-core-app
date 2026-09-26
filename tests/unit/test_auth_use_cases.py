import time

import pytest
from freezegun import freeze_time

from app.application.services.jwt_service import JWTService
from app.application.services.telegram_init_data import TelegramInitDataValidator
from app.application.use_cases.auth import (
    AuthenticateTelegramUserUseCase,
    VerifyAccessTokenUseCase,
)
from app.domain.exceptions import (
    InitDataSignatureInvalidError,
    TokenExpiredError,
    TokenInvalidError,
    UserBannedError,
)
from scripts.dev_gen_init_data import build_init_data
from tests.fixtures.factories import make_user_entity
from tests.fixtures.fake_user_repository import FakeUserRepository

BOT_TOKEN = "123"


@pytest.fixture
def validator() -> TelegramInitDataValidator:
    return TelegramInitDataValidator(bot_token=BOT_TOKEN, max_age_seconds=300)


@pytest.fixture
def jwt_service() -> JWTService:
    return JWTService(secret_key="test-secret", algorithm="HS256", expires_minutes=60)


class TestAuthenticateTelegramUserUseCase:
    async def test_new_user_is_created(self, validator, jwt_service):
        repo = FakeUserRepository()
        use_case = AuthenticateTelegramUserUseCase(repo, validator, jwt_service)
        raw = build_init_data(BOT_TOKEN, 555, int(time.time()), bad_hash=False)

        result = await use_case.execute(raw)

        assert result.is_new_user is True
        assert result.user.telegram_id == 555
        assert await repo.get_by_telegram_id(555) is not None

    async def test_existing_user_is_updated_not_recreated(self, validator, jwt_service):
        existing = make_user_entity(id=1, telegram_id=555, username="old_name")
        repo = FakeUserRepository([existing])
        use_case = AuthenticateTelegramUserUseCase(repo, validator, jwt_service)
        raw = build_init_data(BOT_TOKEN, 555, int(time.time()), bad_hash=False)

        result = await use_case.execute(raw)

        assert result.is_new_user is False
        assert result.user.id == 1
        assert result.user.username == "testuser"  # build_init_data's fixed payload username

    async def test_login_never_touches_ban_or_admin_fields(self, validator, jwt_service):
        existing = make_user_entity(
            id=1, telegram_id=555, is_banned=True, ban_reason="spam", is_admin=True, token_version=4
        )
        repo = FakeUserRepository([existing])
        use_case = AuthenticateTelegramUserUseCase(repo, validator, jwt_service)
        raw = build_init_data(BOT_TOKEN, 555, int(time.time()), bad_hash=False)

        result = await use_case.execute(raw)

        assert result.user.is_banned is True
        assert result.user.ban_reason == "spam"
        assert result.user.is_admin is True
        assert result.user.token_version == 4

    async def test_banned_user_still_authenticates_successfully(self, validator, jwt_service):
        existing = make_user_entity(id=1, telegram_id=555, is_banned=True, ban_reason="spam")
        repo = FakeUserRepository([existing])
        use_case = AuthenticateTelegramUserUseCase(repo, validator, jwt_service)
        raw = build_init_data(BOT_TOKEN, 555, int(time.time()), bad_hash=False)

        result = await use_case.execute(raw)  # must not raise

        assert result.access_token

    async def test_issued_token_reflects_current_token_version_and_is_admin(self, validator, jwt_service):
        existing = make_user_entity(id=1, telegram_id=555, token_version=9, is_admin=True)
        repo = FakeUserRepository([existing])
        use_case = AuthenticateTelegramUserUseCase(repo, validator, jwt_service)
        raw = build_init_data(BOT_TOKEN, 555, int(time.time()), bad_hash=False)

        result = await use_case.execute(raw)
        payload = jwt_service.decode_access_token(result.access_token)

        assert payload.token_version == 9
        assert payload.is_admin is True

    async def test_validator_errors_propagate_unchanged(self, validator, jwt_service):
        repo = FakeUserRepository()
        use_case = AuthenticateTelegramUserUseCase(repo, validator, jwt_service)
        raw = build_init_data(BOT_TOKEN, 555, int(time.time()), bad_hash=True)

        with pytest.raises(InitDataSignatureInvalidError):
            await use_case.execute(raw)


class TestVerifyAccessTokenUseCase:
    async def test_valid_token_returns_user(self, jwt_service):
        user = make_user_entity(id=1, telegram_id=555, token_version=0)
        repo = FakeUserRepository([user])
        use_case = VerifyAccessTokenUseCase(repo, jwt_service)
        token = jwt_service.create_access_token(user_id=1, telegram_id=555, token_version=0, is_admin=False)

        result = await use_case.execute(token)

        assert result.id == 1

    async def test_user_not_found_raises_token_invalid(self, jwt_service):
        repo = FakeUserRepository()
        use_case = VerifyAccessTokenUseCase(repo, jwt_service)
        token = jwt_service.create_access_token(user_id=999, telegram_id=1, token_version=0, is_admin=False)

        with pytest.raises(TokenInvalidError):
            await use_case.execute(token)

    async def test_token_version_mismatch_raises_token_invalid(self, jwt_service):
        user = make_user_entity(id=1, telegram_id=555, token_version=2)
        repo = FakeUserRepository([user])
        use_case = VerifyAccessTokenUseCase(repo, jwt_service)
        token = jwt_service.create_access_token(user_id=1, telegram_id=555, token_version=1, is_admin=False)

        with pytest.raises(TokenInvalidError):
            await use_case.execute(token)

    async def test_banned_user_raises_user_banned_error(self, jwt_service):
        user = make_user_entity(id=1, telegram_id=555, token_version=0, is_banned=True, ban_reason="rules violation")
        repo = FakeUserRepository([user])
        use_case = VerifyAccessTokenUseCase(repo, jwt_service)
        token = jwt_service.create_access_token(user_id=1, telegram_id=555, token_version=0, is_admin=False)

        with pytest.raises(UserBannedError) as exc_info:
            await use_case.execute(token)
        assert exc_info.value.ban_reason == "rules violation"

    async def test_banned_user_with_no_reason(self, jwt_service):
        user = make_user_entity(id=1, telegram_id=555, token_version=0, is_banned=True, ban_reason=None)
        repo = FakeUserRepository([user])
        use_case = VerifyAccessTokenUseCase(repo, jwt_service)
        token = jwt_service.create_access_token(user_id=1, telegram_id=555, token_version=0, is_admin=False)

        with pytest.raises(UserBannedError) as exc_info:
            await use_case.execute(token)
        assert exc_info.value.ban_reason is None

    async def test_expired_token_propagates_from_jwt_service(self, jwt_service):
        repo = FakeUserRepository()
        use_case = VerifyAccessTokenUseCase(repo, jwt_service)
        with freeze_time("2024-01-01T00:00:00Z"):
            token = jwt_service.create_access_token(user_id=1, telegram_id=1, token_version=0, is_admin=False)
        with freeze_time("2024-01-01T02:00:00Z"):
            with pytest.raises(TokenExpiredError):
                await use_case.execute(token)

    async def test_get_by_id_called_once_per_execute(self, jwt_service, monkeypatch):
        user = make_user_entity(id=1, telegram_id=555, token_version=0)
        repo = FakeUserRepository([user])
        calls: list[int] = []
        original = repo.get_by_id

        async def counting_get_by_id(user_id):
            calls.append(user_id)
            return await original(user_id)

        monkeypatch.setattr(repo, "get_by_id", counting_get_by_id)
        use_case = VerifyAccessTokenUseCase(repo, jwt_service)
        token = jwt_service.create_access_token(user_id=1, telegram_id=555, token_version=0, is_admin=False)

        await use_case.execute(token)

        assert calls == [1]
