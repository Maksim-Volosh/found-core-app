from datetime import datetime

from app.domain.entities import NewUserEntity, TelegramUserPayload


def map_telegram_user_payload_to_new_user_entity(payload: TelegramUserPayload, now: datetime) -> NewUserEntity:
    return NewUserEntity(
        telegram_id=payload.id,
        first_name=payload.first_name,
        created_at=now,
        last_active_at=now,
        last_name=payload.last_name,
        username=payload.username,
        photo_url=payload.photo_url,
        language_code=payload.language_code,
    )
