from pydantic import BaseModel, Field

from app.api.v1.schemas.profile import ProfileSchema
from app.api.v1.schemas.user import UserPublicSchema


class TelegramAuthRequest(BaseModel):
    init_data: str = Field(..., min_length=1, max_length=8192)


class TelegramAuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    is_new_user: bool
    user: UserPublicSchema
    profiles: list[ProfileSchema]
