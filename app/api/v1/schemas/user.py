from typing import Optional

from pydantic import BaseModel


class UserRequest(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    first_name: str
    last_name: Optional[str] = None


class UserResponse(BaseModel):
    user_id: int
    telegram_id: int
    username: Optional[str]
    first_name: str
    last_name: Optional[str]
    level: int
    is_banned: bool
    is_admin: bool