from dataclasses import dataclass

from app.domain.entities.user import UserEntity


@dataclass
class TelegramAuthResult:
    user: UserEntity
    access_token: str
    is_new_user: bool
