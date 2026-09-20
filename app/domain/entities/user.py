from dataclasses import dataclass
from datetime import datetime


@dataclass
class NewUserEntity:
    telegram_id: int
    first_name: str
    created_at: datetime
    last_active_at: datetime
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None
    language_code: str | None = None


@dataclass
class UserEntity:
    id: int
    telegram_id: int
    first_name: str
    created_at: datetime
    last_active_at: datetime
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None
    language_code: str | None = None
    terms_accepted_at: datetime | None = None
    is_admin: bool = False
    is_banned: bool = False
    ban_reason: str | None = None
    token_version: int = 0
    active_profile_id: int | None = None
    deleted_at: datetime | None = None
