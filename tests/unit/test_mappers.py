from datetime import datetime, timezone

from app.api.v1.mappers.auth import map_telegram_auth_result_to_telegram_auth_response
from app.api.v1.mappers.user import map_user_entity_to_user_public_schema
from app.domain.entities import TelegramAuthResult
from app.infrastructure.mappers.user_mapper import (
    apply_user_entity_to_user_model,
    map_new_user_entity_to_user_model,
    map_user_model_to_user_entity,
)
from app.infrastructure.models import UserModel
from tests.fixtures.factories import make_new_user_entity, make_user_entity


def test_map_user_entity_to_user_public_schema_passthrough():
    entity = make_user_entity(is_banned=True, ban_reason="spam", is_admin=True)

    schema = map_user_entity_to_user_public_schema(entity)

    assert schema.id == entity.id
    assert schema.telegram_id == entity.telegram_id
    assert schema.is_banned is True
    assert schema.ban_reason == "spam"
    assert schema.is_admin is True


def test_map_telegram_auth_result_to_response_profiles_is_empty():
    entity = make_user_entity()
    result = TelegramAuthResult(user=entity, access_token="tok", is_new_user=True)

    response = map_telegram_auth_result_to_telegram_auth_response(result)

    assert response.profiles == []
    assert response.access_token == "tok"
    assert response.is_new_user is True


def test_map_new_user_entity_to_user_model_round_trip():
    entity = make_new_user_entity(username="new_guy")

    model = map_new_user_entity_to_user_model(entity)

    assert model.telegram_id == entity.telegram_id
    assert model.username == "new_guy"


def test_map_user_model_to_user_entity_round_trip():
    now = datetime.now(timezone.utc)
    model = UserModel(
        id=1,
        telegram_id=555,
        first_name="Test",
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
        created_at=now,
        last_active_at=now,
        deleted_at=None,
    )

    entity = map_user_model_to_user_entity(model)

    assert entity.id == 1
    assert entity.telegram_id == 555


def test_apply_user_entity_to_user_model_only_touches_documented_fields():
    now = datetime.now(timezone.utc)
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
    )

    apply_user_entity_to_user_model(incoming, model)

    assert model.first_name == "New"
    assert model.last_name == "Person"
    assert model.username == "new_username"
    assert model.photo_url == "new.jpg"
    assert model.language_code == "en"
    # Untouched by design -- this is the "re-login can never un-ban a user" guard.
    assert model.is_admin is True
    assert model.is_banned is True
    assert model.ban_reason == "spam"
    assert model.token_version == 5
    assert model.active_profile_id == 42
