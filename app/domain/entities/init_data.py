from dataclasses import dataclass


@dataclass(frozen=True)
class TelegramUserPayload:
    id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None
    language_code: str | None = None


@dataclass(frozen=True)
class TelegramInitData:
    auth_date: int
    user: TelegramUserPayload
