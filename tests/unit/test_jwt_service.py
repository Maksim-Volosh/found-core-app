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
    token = jwt_service.create_access_token(user_id=7, telegram_id=999, token_version=3)

    payload = jwt_service.decode_access_token(token)

    assert payload.user_id == 7
    assert payload.telegram_id == 999
    assert payload.token_version == 3


def test_token_does_not_carry_the_admin_flag(jwt_service):
    # Admin rights are read from the database on every request; a claim here could only be trusted by mistake.
    token = jwt_service.create_access_token(user_id=1, telegram_id=1, token_version=0)

    assert "is_admin" not in jwt.decode(token, SECRET, algorithms=["HS256"])


def test_exp_matches_expires_minutes(jwt_service):
    with freeze_time("2024-01-01T00:00:00Z"):
        token = jwt_service.create_access_token(user_id=1, telegram_id=1, token_version=0)
        # decode within the same frozen instant -- PyJWT validates `exp` against
        # the real wall clock otherwise, and this token is only "not expired"
        # relative to the moment it was minted.
        decoded = jwt.decode(token, SECRET, algorithms=["HS256"])

    assert decoded["exp"] - decoded["iat"] == 60 * 60


def test_expired_token_raises_token_expired_error(jwt_service):
    with freeze_time("2024-01-01T00:00:00Z"):
        token = jwt_service.create_access_token(user_id=1, telegram_id=1, token_version=0)

    with freeze_time("2024-01-01T01:00:01Z"):
        with pytest.raises(TokenExpiredError):
            jwt_service.decode_access_token(token)


def test_garbage_token_raises_token_invalid_error(jwt_service):
    with pytest.raises(TokenInvalidError):
        jwt_service.decode_access_token("not-a-jwt")


def test_token_signed_with_different_secret_is_invalid(jwt_service):
    other = JWTService(secret_key="other-secret", algorithm="HS256", expires_minutes=60)
    token = other.create_access_token(user_id=1, telegram_id=1, token_version=0)

    with pytest.raises(TokenInvalidError):
        jwt_service.decode_access_token(token)


_MISSING = object()


def _forge(secret: str = SECRET, algorithm: str = "HS256", **overrides) -> str:
    """A token with a *valid signature* but hand-picked claims. `_MISSING` drops a claim."""
    now = int(time.time())
    claims = {
        "sub": "1",
        "telegram_id": 1,
        "token_version": 0,
        "iat": now,
        "exp": now + 3600,
        **overrides,
    }
    claims = {k: v for k, v in claims.items() if v is not _MISSING}
    return jwt.encode(claims, secret, algorithm=algorithm)


def test_forged_but_well_formed_token_is_accepted(jwt_service):
    # Guards the helper itself: only the deliberately broken variants below may fail.
    assert jwt_service.decode_access_token(_forge()).user_id == 1


def test_token_issued_before_the_admin_claim_was_dropped_is_still_accepted(jwt_service):
    # Extra claims are ignored, so tokens minted by the previous release keep working until they expire.
    assert jwt_service.decode_access_token(_forge(is_admin=True)).user_id == 1


def test_unsigned_alg_none_token_is_invalid(jwt_service):
    with pytest.raises(TokenInvalidError):
        jwt_service.decode_access_token(_forge(secret="", algorithm="none"))


def test_token_signed_with_another_algorithm_is_invalid(jwt_service):
    with pytest.raises(TokenInvalidError):
        jwt_service.decode_access_token(_forge(algorithm="HS512"))


@pytest.mark.parametrize("claim", ["exp", "iat", "sub", "telegram_id", "token_version"])
def test_token_missing_a_required_claim_is_invalid(jwt_service, claim):
    # A signed token without `exp` would otherwise never expire.
    with pytest.raises(TokenInvalidError):
        jwt_service.decode_access_token(_forge(**{claim: _MISSING}))


@pytest.mark.parametrize("sub", ["not-a-number", "-5", "0", "1.5", "", str(2**63), "9" * 5000, "١٢٣", 5])
def test_invalid_sub_is_token_invalid_not_a_crash(jwt_service, sub):
    with pytest.raises(TokenInvalidError):
        jwt_service.decode_access_token(_forge(sub=sub))


@pytest.mark.parametrize(
    "claim, value",
    [
        ("token_version", "1"),
        ("token_version", True),
        ("token_version", 1.5),
        ("token_version", None),
        ("telegram_id", "5"),
        ("telegram_id", True),
        ("telegram_id", None),
    ],
)
def test_wrongly_typed_claim_is_token_invalid(jwt_service, claim, value):
    with pytest.raises(TokenInvalidError):
        jwt_service.decode_access_token(_forge(**{claim: value}))
