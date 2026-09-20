import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from app.domain.entities import TelegramInitData, TelegramUserPayload
from app.domain.exceptions import (
    InitDataExpiredError,
    InitDataMalformedError,
    InitDataSignatureInvalidError,
)

_WEBAPP_DATA_KEY = b"WebAppData"


class TelegramInitDataValidator:
    def __init__(self, bot_token: str, max_age_seconds: int) -> None:
        self._bot_token = bot_token
        self._max_age_seconds = max_age_seconds

    def validate(self, init_data: str) -> TelegramInitData:
        if not init_data or not init_data.strip():
            raise InitDataMalformedError

        data = dict(parse_qsl(init_data, keep_blank_values=True, strict_parsing=False))

        received_hash = data.pop("hash", None)
        if not received_hash:
            raise InitDataMalformedError

        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
        secret_key = hmac.new(_WEBAPP_DATA_KEY, self._bot_token.encode(), hashlib.sha256).digest()
        expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_hash, received_hash):
            raise InitDataSignatureInvalidError

        auth_date_raw = data.get("auth_date")
        if auth_date_raw is None or not auth_date_raw.isdigit():
            raise InitDataMalformedError
        auth_date = int(auth_date_raw)
        if time.time() - auth_date > self._max_age_seconds:
            raise InitDataExpiredError

        user_raw = data.get("user")
        if not user_raw:
            raise InitDataMalformedError
        try:
            user_json = json.loads(user_raw)
            user_payload = TelegramUserPayload(
                id=int(user_json["id"]),
                first_name=user_json["first_name"],
                last_name=user_json.get("last_name"),
                username=user_json.get("username"),
                photo_url=user_json.get("photo_url"),
                language_code=user_json.get("language_code"),
            )
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise InitDataMalformedError from exc

        return TelegramInitData(auth_date=auth_date, user=user_payload)
