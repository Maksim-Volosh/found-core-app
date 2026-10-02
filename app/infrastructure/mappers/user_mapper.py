from app.domain.entities import UserEntity
from app.infrastructure.models import UserModel


def map_user_model_to_user_entity(model: UserModel) -> UserEntity:
    return UserEntity(
        id=model.id,
        telegram_id=model.telegram_id,
        first_name=model.first_name,
        created_at=model.created_at,
        last_active_at=model.last_active_at,
        last_name=model.last_name,
        username=model.username,
        photo_url=model.photo_url,
        language_code=model.language_code,
        terms_accepted_at=model.terms_accepted_at,
        is_admin=model.is_admin,
        is_banned=model.is_banned,
        ban_reason=model.ban_reason,
        token_version=model.token_version,
        active_profile_id=model.active_profile_id,
        deleted_at=model.deleted_at,
    )


def apply_user_entity_to_user_model(entity: UserEntity, model: UserModel) -> None:
    model.first_name = entity.first_name
    model.last_name = entity.last_name
    model.username = entity.username
    model.photo_url = entity.photo_url
    model.language_code = entity.language_code
    model.last_active_at = entity.last_active_at
