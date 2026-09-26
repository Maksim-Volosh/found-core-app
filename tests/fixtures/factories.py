from datetime import datetime, timezone

from app.domain.entities import NewUserEntity, UserEntity


def make_new_user_entity(**overrides) -> NewUserEntity:
    now = datetime.now(timezone.utc)
    defaults = dict(
        telegram_id=123456789,
        first_name="Test",
        created_at=now,
        last_active_at=now,
        last_name=None,
        username="testuser",
        photo_url=None,
        language_code="en",
    )
    defaults.update(overrides)
    return NewUserEntity(**defaults)


def make_user_entity(**overrides) -> UserEntity:
    now = datetime.now(timezone.utc)
    defaults = dict(
        id=1,
        telegram_id=123456789,
        first_name="Test",
        created_at=now,
        last_active_at=now,
        last_name=None,
        username="testuser",
        photo_url=None,
        language_code="en",
        terms_accepted_at=None,
        is_admin=False,
        is_banned=False,
        ban_reason=None,
        token_version=0,
        active_profile_id=None,
        deleted_at=None,
    )
    defaults.update(overrides)
    return UserEntity(**defaults)
