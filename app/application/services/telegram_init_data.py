import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from app.domain.constants import MAX_INT64
from app.domain.entities import TelegramInitData, TelegramUserPayload
from app.domain.exceptions import (
    InitDataExpiredError,
    InitDataMalformedError,
    InitDataSignatureInvalidError,
)

_WEBAPP_DATA_KEY = b"WebAppData"

# Mirror the `users` column sizes: a longer value would fail at INSERT time.
_FIRST_NAME_MAX_LENGTH = 255
_LAST_NAME_MAX_LENGTH = 255
_USERNAME_MAX_LENGTH = 255
_PHOTO_URL_MAX_LENGTH = 1024
_LANGUAGE_CODE_MAX_LENGTH = 16

# Python refuses to int() strings of thousands of digits; a real unix timestamp has 10.
_AUTH_DATE_MAX_DIGITS = 15


def _optional_str(payload: dict, key: str, max_length: int) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    # Postgres cannot store NUL characters in text columns.
    if not isinstance(value, str) or len(value) > max_length or "\x00" in value:
        raise InitDataMalformedError
    return value


def _required_str(payload: dict, key: str, max_length: int) -> str:
    value = _optional_str(payload, key, max_length)
    if not value:
        raise InitDataMalformedError
    return value


class TelegramInitDataValidator:
    def __init__(self, bot_token: str, max_age_seconds: int, max_future_skew_seconds: int) -> None:
        self._bot_token = bot_token
        self._max_age_seconds = max_age_seconds
        self._max_future_skew_seconds = max_future_skew_seconds

    def validate(self, init_data: str) -> TelegramInitData:
        if not init_data or not init_data.strip():
            raise InitDataMalformedError

        pairs = parse_qsl(init_data, keep_blank_values=True, strict_parsing=False)
        data = dict(pairs)
        if len(data) != len(pairs):
            raise InitDataMalformedError  # a key (including `hash`) was sent more than once

        received_hash = data.pop("hash", None)
        if not received_hash:
            raise InitDataMalformedError

        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
        secret_key = hmac.new(_WEBAPP_DATA_KEY, self._bot_token.encode(), hashlib.sha256).digest()
        expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        # Compared as bytes: compare_digest raises TypeError on non-ASCII str.
        if not hmac.compare_digest(expected_hash.encode(), received_hash.encode()):
            raise InitDataSignatureInvalidError

        auth_date = self._parse_auth_date(data.get("auth_date"))

        return TelegramInitData(auth_date=auth_date, user=self._parse_user(data.get("user")))

    def _parse_auth_date(self, raw: str | None) -> int:
        if raw is None or not (raw.isascii() and raw.isdigit()) or len(raw) > _AUTH_DATE_MAX_DIGITS:
            raise InitDataMalformedError
        auth_date = int(raw)

        now = time.time()
        if auth_date - now > self._max_future_skew_seconds:
            raise InitDataMalformedError
        if now - auth_date > self._max_age_seconds:
            raise InitDataExpiredError
        return auth_date

    @staticmethod
    def _parse_user(raw: str | None) -> TelegramUserPayload:
        if not raw:
            raise InitDataMalformedError
        try:
            user_json = json.loads(raw)
        except (json.JSONDecodeError, RecursionError) as exc:
            raise InitDataMalformedError from exc
        if not isinstance(user_json, dict):
            raise InitDataMalformedError

        user_id = user_json.get("id")
        # `type(...) is int` also rejects bool, which is an int subclass.
        if type(user_id) is not int or not 0 < user_id <= MAX_INT64:
            raise InitDataMalformedError

        return TelegramUserPayload(
            id=user_id,
            first_name=_required_str(user_json, "first_name", _FIRST_NAME_MAX_LENGTH),
            last_name=_optional_str(user_json, "last_name", _LAST_NAME_MAX_LENGTH),
            username=_optional_str(user_json, "username", _USERNAME_MAX_LENGTH),
            photo_url=_optional_str(user_json, "photo_url", _PHOTO_URL_MAX_LENGTH),
            language_code=_optional_str(user_json, "language_code", _LANGUAGE_CODE_MAX_LENGTH),
        )
