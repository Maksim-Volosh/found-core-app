from dataclasses import dataclass
from enum import Enum


class ScreeningStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    APPROVED = "APPROVED"

@dataclass
class DirectionEntity:
    telegram_chat_id: int
    name: str
    owner_username: str
    requires_screening: bool
    
@dataclass
class UserDirectionAccessEntity:
    user_id: int
    telegram_chat_id: int
    screening_status: ScreeningStatus