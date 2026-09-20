"""Dev-only: генерирует валидный (или просроченный/битый) Telegram initData
для ручного теста POST /api/v1/auth/telegram, подписывая тем же BOT_TOKEN,
что задан в .env (APP_CONFIG__BOT__TOKEN).

Использование:
    python scripts/dev_gen_init_data.py
    python scripts/dev_gen_init_data.py --expired
    python scripts/dev_gen_init_data.py --bad-hash
    python scripts/dev_gen_init_data.py --telegram-id 555 --bot-token 123
"""

import argparse
import hashlib
import hmac
import json
import time
import urllib.parse

WEBAPP_DATA_KEY = b"WebAppData"


def build_init_data(bot_token: str, telegram_id: int, auth_date: int, bad_hash: bool) -> str:
    user = {
        "id": telegram_id,
        "first_name": "Test",
        "last_name": "User",
        "username": "testuser",
        "language_code": "en",
    }
    params = {
        "query_id": "AAHdF6IQAAAAAN0XohDhrOrc",
        "user": json.dumps(user, separators=(",", ":")),
        "auth_date": str(auth_date),
    }
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret_key = hmac.new(WEBAPP_DATA_KEY, bot_token.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    params["hash"] = "0" * 64 if bad_hash else computed_hash
    return "&".join(f"{k}={urllib.parse.quote(v, safe='')}" for k, v in params.items())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bot-token", default="123")
    parser.add_argument("--telegram-id", type=int, default=123456789)
    parser.add_argument("--expired", action="store_true", help="auth_date на 400 сек в прошлом")
    parser.add_argument("--bad-hash", action="store_true", help="испортить hash")
    args = parser.parse_args()

    auth_date = int(time.time()) - (400 if args.expired else 0)
    init_data = build_init_data(args.bot_token, args.telegram_id, auth_date, args.bad_hash)

    print(init_data)
    print()
    print("curl -X POST http://localhost:8000/api/v1/auth/telegram \\")
    print("  -H 'Content-Type: application/json' \\")
    print(f"  -d '{json.dumps({'init_data': init_data})}'")


if __name__ == "__main__":
    main()
