from app.api.v1.schemas import UserPublicSchema
from app.domain.entities import UserEntity


def map_user_entity_to_user_public_schema(entity: UserEntity) -> UserPublicSchema:
    return UserPublicSchema(
        id=entity.id,
        telegram_id=entity.telegram_id,
        first_name=entity.first_name,
        last_name=entity.last_name,
        username=entity.username,
        photo_url=entity.photo_url,
        is_admin=entity.is_admin,
        is_banned=entity.is_banned,
        ban_reason=entity.ban_reason,
    )
