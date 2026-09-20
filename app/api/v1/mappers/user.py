from app.api.v1.schemas.user import TelegramAuthResponse, UserPublicSchema
from app.domain.entities.auth import TelegramAuthResult
from app.domain.entities.user import UserEntity


def map_user_entity_to_public_schema(entity: UserEntity) -> UserPublicSchema:
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


def map_auth_result_to_response(result: TelegramAuthResult) -> TelegramAuthResponse:
    return TelegramAuthResponse(
        access_token=result.access_token,
        is_new_user=result.is_new_user,
        user=map_user_entity_to_public_schema(result.user),
        profiles=[],
    )
