import time

import pytest
from freezegun import freeze_time

from app.application.services.telegram_init_data import TelegramInitDataValidator
from app.domain.exceptions import (
    InitDataExpiredError,
    InitDataMalformedError,
    InitDataSignatureInvalidError,
)
from scripts.dev_gen_init_data import build_init_data
from tests.fixtures.init_data import (
    BOT_TOKEN,
    bad_hash_init_data,
    init_data_missing_field,
    init_data_missing_hash,
    init_data_with_broken_user_json,
    init_data_with_minimal_user,
    init_data_with_non_digit_auth_date,
    init_data_with_user_missing_required_field,
    valid_init_data,
)


@pytest.fixture
def validator() -> TelegramInitDataValidator:
    return TelegramInitDataValidator(bot_token=BOT_TOKEN, max_age_seconds=300)


def test_valid_init_data_parses(validator):
    parsed = validator.validate(valid_init_data(42))

    assert parsed.user.id == 42
    assert parsed.user.first_name == "Test"
    assert parsed.user.username == "testuser"


@pytest.mark.parametrize("raw", ["", "   "])
def test_empty_or_blank_init_data_is_malformed(validator, raw):
    with pytest.raises(InitDataMalformedError):
        validator.validate(raw)


def test_missing_hash_is_malformed(validator):
    with pytest.raises(InitDataMalformedError):
        validator.validate(init_data_missing_hash(42))


def test_tampered_hash_is_signature_invalid(validator):
    with pytest.raises(InitDataSignatureInvalidError):
        validator.validate(bad_hash_init_data(42))


def test_missing_auth_date_is_malformed(validator):
    with pytest.raises(InitDataMalformedError):
        validator.validate(init_data_missing_field(42, "auth_date"))


def test_non_digit_auth_date_is_malformed(validator):
    with pytest.raises(InitDataMalformedError):
        validator.validate(init_data_with_non_digit_auth_date(42))


def test_auth_date_exactly_at_ttl_boundary_is_still_valid(validator):
    # Strict `>` check in the validator: diff == max_age_seconds must NOT raise.
    with freeze_time("2024-01-01T00:00:00Z"):
        auth_date = int(time.time()) - 300
        raw = build_init_data(BOT_TOKEN, 42, auth_date, bad_hash=False)
        validator.validate(raw)


def test_auth_date_one_second_past_ttl_boundary_is_expired(validator):
    with freeze_time("2024-01-01T00:00:00Z"):
        auth_date = int(time.time()) - 301
        raw = build_init_data(BOT_TOKEN, 42, auth_date, bad_hash=False)
        with pytest.raises(InitDataExpiredError):
            validator.validate(raw)


def test_missing_user_field_is_malformed(validator):
    with pytest.raises(InitDataMalformedError):
        validator.validate(init_data_missing_field(42, "user"))


def test_broken_user_json_is_malformed(validator):
    with pytest.raises(InitDataMalformedError):
        validator.validate(init_data_with_broken_user_json())


@pytest.mark.parametrize("field", ["id", "first_name"])
def test_user_missing_required_field_is_malformed(validator, field):
    with pytest.raises(InitDataMalformedError):
        validator.validate(init_data_with_user_missing_required_field(42, field))


def test_optional_user_fields_absent_parse_as_none(validator):
    parsed = validator.validate(init_data_with_minimal_user(42))

    assert parsed.user.last_name is None
    assert parsed.user.username is None
    assert parsed.user.photo_url is None
    assert parsed.user.language_code is None
