import time

import jwt
import pytest
from freezegun import freeze_time

from app.application.services.jwt_service import JWTService
from app.domain.exceptions import TokenExpiredError, TokenInvalidError

SECRET = "test-secret"


@pytest.fixture
def jwt_service() -> JWTService:
    return JWTService(secret_key=SECRET, algorithm="HS256", expires_minutes=60)


def test_round_trip_preserves_claims(jwt_service):
    token = jwt_service.create_access_token(user_id=7, telegram_id=999, token_version=3, is_admin=True)

    payload = jwt_service.decode_access_token(token)

    assert payload.user_id == 7
    assert payload.telegram_id == 999
    assert payload.token_version == 3
    assert payload.is_admin is True


def test_exp_matches_expires_minutes(jwt_service):
    with freeze_time("2024-01-01T00:00:00Z"):
        token = jwt_service.create_access_token(user_id=1, telegram_id=1, token_version=0, is_admin=False)
        # decode within the same frozen instant -- PyJWT validates `exp` against
        # the real wall clock otherwise, and this token is only "not expired"
        # relative to the moment it was minted.
        decoded = jwt.decode(token, SECRET, algorithms=["HS256"])

    assert decoded["exp"] - decoded["iat"] == 60 * 60


def test_expired_token_raises_token_expired_error(jwt_service):
    with freeze_time("2024-01-01T00:00:00Z"):
        token = jwt_service.create_access_token(user_id=1, telegram_id=1, token_version=0, is_admin=False)

    with freeze_time("2024-01-01T01:00:01Z"):
        with pytest.raises(TokenExpiredError):
            jwt_service.decode_access_token(token)


def test_garbage_token_raises_token_invalid_error(jwt_service):
    with pytest.raises(TokenInvalidError):
        jwt_service.decode_access_token("not-a-jwt")


def test_token_signed_with_different_secret_is_invalid(jwt_service):
    other = JWTService(secret_key="other-secret", algorithm="HS256", expires_minutes=60)
    token = other.create_access_token(user_id=1, telegram_id=1, token_version=0, is_admin=False)

    with pytest.raises(TokenInvalidError):
        jwt_service.decode_access_token(token)


def test_valid_signature_with_non_numeric_sub_raises_raw_value_error(jwt_service):
    """Documents a known gap, not a required behavior: `decode_access_token` casts
    `payload["sub"]` to `int` without catching `ValueError`, so a validly-signed
    token with a non-numeric `sub` surfaces as a raw `ValueError`, not
    `TokenInvalidError`. Only reachable with a forged-but-correctly-signed token.
    Flagged as a follow-up fix; this test just pins current behavior."""
    forged = jwt.encode(
        {
            "sub": "not-a-number",
            "telegram_id": 1,
            "token_version": 0,
            "is_admin": False,
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
        },
        SECRET,
        algorithm="HS256",
    )

    with pytest.raises(ValueError):
        jwt_service.decode_access_token(forged)
