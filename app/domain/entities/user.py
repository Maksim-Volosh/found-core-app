from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


@dataclass
class UserEntity:
    user_id: int
    telegram_id: int
    username: Optional[str]
    first_name: str
    last_name: Optional[str]
    level: int
    created_at: datetime
    updated_at: datetime
    is_banned: bool
    is_admin: bool