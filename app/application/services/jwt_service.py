from datetime import datetime, timedelta, timezone

import jwt


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
