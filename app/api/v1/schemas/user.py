from typing import Optional

from pydantic import BaseModel


class AuthUserRequest(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    first_name: str
    last_name: Optional[str] = None