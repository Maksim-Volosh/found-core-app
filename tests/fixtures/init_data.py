"""Builders for Telegram `initData` payloads used across the test suite.

Reuses the exact HMAC-signing algorithm from `scripts/dev_gen_init_data.py`
(single source of truth with the real validator) for the valid / expired /
bad-hash cases, and adds a few malformed-shape variants the dev script has no
option for (it only supports valid, `--expired`, `--bad-hash`).
"""

import hashlib
import hmac
import json
import time
import urllib.parse

from scripts.dev_gen_init_data import WEBAPP_DATA_KEY, build_init_data

BOT_TOKEN = "123"

__all__ = [
    "BOT_TOKEN",
    "valid_init_data",
    "expired_init_data",
    "bad_hash_init_data",
    "init_data_missing_hash",
    "init_data_missing_field",
    "init_data_with_username",
    "init_data_with_broken_user_json",
    "init_data_with_user_missing_required_field",
    "init_data_with_non_digit_auth_date",
    "init_data_with_minimal_user",
]

_QUERY_ID = "AAHdF6IQAAAAAN0XohDhrOrc"


def valid_init_data(telegram_id: int, bot_token: str = BOT_TOKEN) -> str:
    return build_init_data(bot_token, telegram_id, int(time.time()), bad_hash=False)


def expired_init_data(telegram_id: int, ttl_seconds: int = 300, bot_token: str = BOT_TOKEN) -> str:
    auth_date = int(time.time()) - ttl_seconds - 1
    return build_init_data(bot_token, telegram_id, auth_date, bad_hash=False)


def bad_hash_init_data(telegram_id: int, bot_token: str = BOT_TOKEN) -> str:
    return build_init_data(bot_token, telegram_id, int(time.time()), bad_hash=True)


def init_data_missing_hash(telegram_id: int, bot_token: str = BOT_TOKEN) -> str:
    raw = valid_init_data(telegram_id, bot_token)
    return "&".join(p for p in raw.split("&") if not p.startswith("hash="))


def _sign(bot_token: str, params: dict) -> str:
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret_key = hmac.new(WEBAPP_DATA_KEY, bot_token.encode(), hashlib.sha256).digest()
    signed = {**params, "hash": hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()}
    return "&".join(f"{k}={urllib.parse.quote(v, safe='')}" for k, v in signed.items())


def _user_json(telegram_id: int, **overrides) -> str:
    user = {
        "id": telegram_id,
        "first_name": "Test",
        "last_name": "User",
        "username": "testuser",
        "language_code": "en",
        **overrides,
    }
    return json.dumps(user, separators=(",", ":"))


def init_data_with_username(telegram_id: int, username: str, bot_token: str = BOT_TOKEN) -> str:
    params = {
        "query_id": _QUERY_ID,
        "user": _user_json(telegram_id, username=username),
        "auth_date": str(int(time.time())),
    }
    return _sign(bot_token, params)


def init_data_missing_field(telegram_id: int, field: str, bot_token: str = BOT_TOKEN) -> str:
    """`field` is one of the top-level params: "user" or "auth_date"."""
    params = {
        "query_id": _QUERY_ID,
        "user": _user_json(telegram_id),
        "auth_date": str(int(time.time())),
    }
    params.pop(field, None)
    return _sign(bot_token, params)


def init_data_with_broken_user_json(bot_token: str = BOT_TOKEN) -> str:
    params = {
        "query_id": _QUERY_ID,
        "user": "{not-valid-json",
        "auth_date": str(int(time.time())),
    }
    return _sign(bot_token, params)


def init_data_with_user_missing_required_field(telegram_id: int, field: str, bot_token: str = BOT_TOKEN) -> str:
    """`field` is one of the nested user JSON fields, e.g. "id" or "first_name"."""
    user = {
        "id": telegram_id,
        "first_name": "Test",
        "last_name": "User",
        "username": "testuser",
        "language_code": "en",
    }
    user.pop(field, None)
    params = {
        "query_id": _QUERY_ID,
        "user": json.dumps(user, separators=(",", ":")),
        "auth_date": str(int(time.time())),
    }
    return _sign(bot_token, params)


def init_data_with_non_digit_auth_date(telegram_id: int, bot_token: str = BOT_TOKEN) -> str:
    params = {
        "query_id": _QUERY_ID,
        "user": _user_json(telegram_id),
        "auth_date": "not-a-number",
    }
    return _sign(bot_token, params)


def init_data_with_minimal_user(telegram_id: int, bot_token: str = BOT_TOKEN) -> str:
    """Only the two required user fields -- confirms optional fields parse as None."""
    params = {
        "query_id": _QUERY_ID,
        "user": json.dumps({"id": telegram_id, "first_name": "Test"}, separators=(",", ":")),
        "auth_date": str(int(time.time())),
    }
    return _sign(bot_token, params)
