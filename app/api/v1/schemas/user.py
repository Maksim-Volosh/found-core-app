from pydantic import BaseModel, ConfigDict


class UserPublicSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    telegram_id: int
    first_name: str
    last_name: str | None
    username: str | None
    photo_url: str | None
    is_admin: bool
    is_banned: bool
    ban_reason: str | None
