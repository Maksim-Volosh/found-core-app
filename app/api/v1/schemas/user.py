from typing import Optional

from pydantic import BaseModel


class UserRequest(BaseModel):
    telegram_id: int

class UserResponse(BaseModel):
    user_id: int
    telegram_id: int
    username: str
    first_name: str
    level: int
    is_banned: bool