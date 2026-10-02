from datetime import datetime, timedelta, timezone

import jwt

from app.domain.constants import MAX_INT64
from app.domain.entities import AccessTokenPayload
from app.domain.exceptions import TokenExpiredError, TokenInvalidError

_REQUIRED_CLAIMS = ["exp", "iat", "sub", "telegram_id", "token_version", "is_admin"]

# len(str(MAX_INT64)); also keeps int() away from absurdly long digit strings.
_SUB_MAX_DIGITS = 19


class JWTService:
    def __init__(self, secret_key: str, algorithm: str, expires_minutes: int) -> None:
        self._secret_key = secret_key
        self._algorithm = algorithm
        self._expires_minutes = expires_minutes

    def create_access_token(
        self, *, user_id: int, telegram_id: int, token_version: int, is_admin: bool
    ) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user_id),
            "telegram_id": telegram_id,
            "token_version": token_version,
            "is_admin": is_admin,
            "iat": now,
            "exp": now + timedelta(minutes=self._expires_minutes),
        }
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def decode_access_token(self, token: str) -> AccessTokenPayload:
        try:
            payload = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._algorithm],
                options={"require": _REQUIRED_CLAIMS},
            )
        except jwt.ExpiredSignatureError as exc:
            raise TokenExpiredError() from exc
        except jwt.InvalidTokenError as exc:
            raise TokenInvalidError() from exc

        sub = payload["sub"]
        telegram_id = payload["telegram_id"]
        token_version = payload["token_version"]
        is_admin = payload["is_admin"]

        # `type(...) is int` also rejects bool, which is an int subclass.
        if (
            not isinstance(sub, str)
            or not (sub.isascii() and sub.isdigit())
            or len(sub) > _SUB_MAX_DIGITS
            or not 0 < int(sub) <= MAX_INT64
            or type(telegram_id) is not int
            or type(token_version) is not int
            or type(is_admin) is not bool
        ):
            raise TokenInvalidError()

        return AccessTokenPayload(
            user_id=int(sub),
            telegram_id=telegram_id,
            token_version=token_version,
            is_admin=is_admin,
        )
