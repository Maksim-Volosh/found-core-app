from datetime import datetime, timezone

from app.api.v1.mappers.auth import map_telegram_auth_result_to_telegram_auth_response
from app.api.v1.mappers.user import map_user_entity_to_user_public_schema
from app.domain.entities import NewUserEntity, TelegramAuthResult, TelegramUserPayload, UserEntity
from app.domain.mappers.telegram_user import map_telegram_user_payload_to_new_user_entity
from app.infrastructure.mappers.user_mapper import (
    apply_user_entity_to_user_model,
    map_user_model_to_user_entity,
)
from app.infrastructure.models import UserModel
from tests.fixtures.factories import make_user_entity


def test_map_user_entity_to_user_public_schema_passthrough():
    entity = make_user_entity(is_banned=True, ban_reason="spam", is_admin=True)

    schema = map_user_entity_to_user_public_schema(entity)

    assert schema.id == entity.id
    assert schema.telegram_id == entity.telegram_id
    assert schema.is_banned is True
    assert schema.ban_reason == "spam"
    assert schema.is_admin is True


def test_map_telegram_user_payload_to_new_user_entity_copies_every_field():
    now = datetime.now(timezone.utc)
    payload = TelegramUserPayload(
        id=555,
        first_name="Test",
        last_name="User",
        username="testuser",
        photo_url="https://example.com/a.jpg",
        language_code="en",
    )

    entity = map_telegram_user_payload_to_new_user_entity(payload, now)

    assert entity == NewUserEntity(
        telegram_id=555,
        first_name="Test",
        created_at=now,
        last_active_at=now,
        last_name="User",
        username="testuser",
        photo_url="https://example.com/a.jpg",
        language_code="en",
    )


def test_map_telegram_user_payload_to_new_user_entity_keeps_absent_optionals_as_none():
    now = datetime.now(timezone.utc)

    entity = map_telegram_user_payload_to_new_user_entity(TelegramUserPayload(id=1, first_name="Only"), now)

    assert entity.last_name is None
    assert entity.username is None
    assert entity.photo_url is None
    assert entity.language_code is None


def test_map_telegram_auth_result_to_response_profiles_is_empty():
    entity = make_user_entity()
    result = TelegramAuthResult(user=entity, access_token="tok", is_new_user=True)

    response = map_telegram_auth_result_to_telegram_auth_response(result)

    assert response.profiles == []
    assert response.access_token == "tok"
    assert response.is_new_user is True


def test_map_user_model_to_user_entity_copies_every_field():
    # Every value is different, so a swapped or dropped field fails the comparison.
    created = datetime(2024, 1, 1, tzinfo=timezone.utc)
    active = datetime(2024, 2, 2, tzinfo=timezone.utc)
    terms = datetime(2024, 3, 3, tzinfo=timezone.utc)
    deleted = datetime(2024, 4, 4, tzinfo=timezone.utc)
    model = UserModel(
        id=11,
        telegram_id=555,
        first_name="First",
        last_name="Last",
        username="uname",
        photo_url="https://example.com/p.jpg",
        language_code="ru",
        terms_accepted_at=terms,
        is_admin=True,
        is_banned=True,
        ban_reason="spam",
        token_version=7,
        active_profile_id=42,
        created_at=created,
        last_active_at=active,
        deleted_at=deleted,
    )

    entity = map_user_model_to_user_entity(model)

    assert entity == UserEntity(
        id=11,
        telegram_id=555,
        first_name="First",
        created_at=created,
        last_active_at=active,
        last_name="Last",
        username="uname",
        photo_url="https://example.com/p.jpg",
        language_code="ru",
        terms_accepted_at=terms,
        is_admin=True,
        is_banned=True,
        ban_reason="spam",
        token_version=7,
        active_profile_id=42,
        deleted_at=deleted,
    )


def test_apply_user_entity_to_user_model_only_touches_documented_fields():
    now = datetime(2024, 1, 1, tzinfo=timezone.utc)
    later = datetime(2024, 6, 1, tzinfo=timezone.utc)
    model = UserModel(
        id=1,
        telegram_id=555,
        first_name="Old",
        last_name="Name",
        username="old_username",
        photo_url="old.jpg",
        language_code="ru",
        is_admin=True,
        is_banned=True,
        ban_reason="spam",
        token_version=5,
        active_profile_id=42,
        created_at=now,
        last_active_at=now,
    )
    incoming = make_user_entity(
        id=1,
        telegram_id=555,
        first_name="New",
        last_name="Person",
        username="new_username",
        photo_url="new.jpg",
        language_code="en",
        is_admin=False,
        is_banned=False,
        ban_reason=None,
        token_version=0,
        active_profile_id=None,
        last_active_at=later,
    )

    apply_user_entity_to_user_model(incoming, model)

    assert model.first_name == "New"
    assert model.last_name == "Person"
    assert model.username == "new_username"
    assert model.photo_url == "new.jpg"
    assert model.language_code == "en"
    assert model.last_active_at == later
    assert model.created_at == now
    # Untouched by design -- this is the "re-login can never un-ban a user" guard.
    assert model.is_admin is True
    assert model.is_banned is True
    assert model.ban_reason == "spam"
    assert model.token_version == 5
    assert model.active_profile_id == 42
