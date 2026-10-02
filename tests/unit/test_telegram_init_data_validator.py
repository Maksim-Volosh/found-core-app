import time
import urllib.parse

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
    init_data_with_duplicate_hash,
    init_data_with_hash_value,
    init_data_with_minimal_user,
    init_data_with_non_digit_auth_date,
    init_data_with_tampered_user,
    init_data_with_user_missing_required_field,
    init_data_with_user_payload,
    valid_init_data,
)


@pytest.fixture
def validator() -> TelegramInitDataValidator:
    return TelegramInitDataValidator(bot_token=BOT_TOKEN, max_age_seconds=300, max_future_skew_seconds=60)


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


class TestSignature:
    @pytest.mark.parametrize("hash_value", ["é", "\u202E", "abc", "0" * 63, "0" * 65, "g" * 64])
    def test_wrong_or_non_ascii_hash_is_signature_invalid(self, validator, hash_value):
        # Non-ASCII used to blow up hmac.compare_digest with TypeError (HTTP 500).
        with pytest.raises(InitDataSignatureInvalidError):
            validator.validate(init_data_with_hash_value(42, hash_value))

    def test_hash_sent_twice_is_malformed(self, validator):
        with pytest.raises(InitDataMalformedError):
            validator.validate(init_data_with_duplicate_hash(42))

    def test_signed_with_another_bot_token_is_signature_invalid(self, validator):
        with pytest.raises(InitDataSignatureInvalidError):
            validator.validate(valid_init_data(42, bot_token="some-other-bot-token"))

    def test_user_swapped_after_signing_is_signature_invalid(self, validator):
        with pytest.raises(InitDataSignatureInvalidError):
            validator.validate(init_data_with_tampered_user(signed_for_id=42, claimed_id=1))

    def test_unknown_but_signed_extra_field_is_accepted(self, validator):
        # Telegram adds new parameters over time; they are covered by the signature.
        raw = init_data_with_user_payload({"id": 42, "first_name": "Test"}, extra_params={"signature": "abc"})

        assert validator.validate(raw).user.id == 42


class TestAuthDate:
    def test_far_future_auth_date_is_malformed(self, validator):
        raw = init_data_with_user_payload({"id": 42, "first_name": "Test"}, auth_date=str(int(time.time()) + 3600))

        with pytest.raises(InitDataMalformedError):
            validator.validate(raw)

    def test_slightly_future_auth_date_within_skew_is_accepted(self, validator):
        raw = init_data_with_user_payload({"id": 42, "first_name": "Test"}, auth_date=str(int(time.time()) + 30))

        validator.validate(raw)

    @pytest.mark.parametrize("auth_date", ["²", "١٢٣", "-5", "1.5", "", " 123", "9" * 5000])
    def test_non_ascii_or_non_integer_auth_date_is_malformed(self, validator, auth_date):
        raw = init_data_with_user_payload({"id": 42, "first_name": "Test"}, auth_date=auth_date)

        with pytest.raises(InitDataMalformedError):
            validator.validate(raw)


class TestUserShape:
    @pytest.mark.parametrize("user", ["[]", '"text"', "123", "null", "true", "[" * 10000, "{not json"])
    def test_user_that_is_not_a_json_object_is_malformed(self, validator, user):
        with pytest.raises(InitDataMalformedError):
            validator.validate(init_data_with_user_payload(user))

    @pytest.mark.parametrize("bad_id", ["42", True, False, 0, -5, 1.5, None, 2**63, [42]])
    def test_invalid_telegram_id_is_malformed(self, validator, bad_id):
        with pytest.raises(InitDataMalformedError):
            validator.validate(init_data_with_user_payload({"id": bad_id, "first_name": "Test"}))

    @pytest.mark.parametrize("bad_name", [5, "", None, ["a"], "a" * 256, "bad\x00name"])
    def test_invalid_first_name_is_malformed(self, validator, bad_name):
        with pytest.raises(InitDataMalformedError):
            validator.validate(init_data_with_user_payload({"id": 42, "first_name": bad_name}))

    @pytest.mark.parametrize(
        "field, bad_value",
        [
            ("last_name", 5),
            ("last_name", {"a": 1}),
            ("last_name", "a" * 256),
            ("username", 5),
            ("username", "a" * 256),
            ("photo_url", "a" * 1025),
            ("photo_url", ["x"]),
            ("language_code", "x" * 17),
            ("language_code", 7),
            ("username", "bad\x00name"),
        ],
    )
    def test_invalid_optional_field_is_malformed(self, validator, field, bad_value):
        payload = {"id": 42, "first_name": "Test", field: bad_value}

        with pytest.raises(InitDataMalformedError):
            validator.validate(init_data_with_user_payload(payload))

    def test_boundary_values_are_accepted(self, validator):
        payload = {
            "id": 2**63 - 1,
            "first_name": "a" * 255,
            "last_name": "b" * 255,
            "username": "c" * 255,
            "photo_url": "d" * 1024,
            "language_code": "e" * 16,
        }

        parsed = validator.validate(init_data_with_user_payload(payload))

        assert parsed.user.id == 2**63 - 1
        assert len(parsed.user.first_name) == 255
        assert len(parsed.user.photo_url) == 1024


class TestKnownSignatureVector:
    """The hash below was computed with `openssl`, not with our Python code, so these
    tests fail if the validator misreads Telegram's algorithm (every other test signs
    with the same algorithm it verifies with).

    bot token "123", data-check-string:
        auth_date=1700000000
        query_id=AAHdF6IQAAAAAN0XohDhrOrc
        user={"id":42,"first_name":"Test","username":"testuser"}
    """

    HASH = "009127bf68106990f0ab66694fe79c1aa47b073939d5d7b0be12c87c0398d84b"
    NOW = "2023-11-14T22:13:20Z"  # == auth_date 1700000000

    @staticmethod
    def _init_data(hash_value: str) -> str:
        return urllib.parse.urlencode(
            {
                "query_id": "AAHdF6IQAAAAAN0XohDhrOrc",
                "user": '{"id":42,"first_name":"Test","username":"testuser"}',
                "auth_date": "1700000000",
                "hash": hash_value,
            }
        )

    def test_signature_computed_by_openssl_is_accepted(self, validator):
        with freeze_time(self.NOW):
            parsed = validator.validate(self._init_data(self.HASH))

        assert parsed.user.id == 42
        assert parsed.user.username == "testuser"

    def test_one_changed_character_in_the_hash_is_rejected(self, validator):
        tampered = self.HASH[:-1] + ("0" if self.HASH[-1] != "0" else "1")

        with freeze_time(self.NOW), pytest.raises(InitDataSignatureInvalidError):
            validator.validate(self._init_data(tampered))

    def test_same_hash_with_another_bot_token_is_rejected(self):
        other_bot = TelegramInitDataValidator(bot_token="124", max_age_seconds=300, max_future_skew_seconds=60)

        with freeze_time(self.NOW), pytest.raises(InitDataSignatureInvalidError):
            other_bot.validate(self._init_data(self.HASH))
