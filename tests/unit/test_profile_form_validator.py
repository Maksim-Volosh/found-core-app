import pytest

from app.core.config import ProfileConfig
from app.domain.entities import ProfileFormEntity
from app.domain.exceptions import (
    InvalidCountryError,
    InvalidProfileTextError,
    InvalidTimezoneError,
    ProfileTagInvalidError,
    TooFewTagsError,
    TooManyTagsError,
)
from app.domain.services import ProfileFormValidator

_config = ProfileConfig()
_TIMEZONES = {"DE": ["Europe/Berlin"], "RU": ["Europe/Moscow", "Asia/Yekaterinburg"]}
_TEXT = "x" * 200


@pytest.fixture
def validator() -> ProfileFormValidator:
    return ProfileFormValidator(
        bio_min_length=_config.bio_min_length,
        bio_max_length=_config.bio_max_length,
        goals_min_length=_config.goals_min_length,
        goals_max_length=_config.goals_max_length,
        tags_min_count=_config.tags_min_count,
        tags_max_count=_config.tags_max_count,
        timezones_by_country=_TIMEZONES,
    )


def _form(**overrides) -> ProfileFormEntity:
    values = {
        "country_code": "DE",
        "timezone": "Europe/Berlin",
        "bio": _TEXT,
        "goals_description": _TEXT,
        "tag_ids": [1, 2, 3, 4, 5],
    }
    values.update(overrides)
    return ProfileFormEntity(**values)


def test_valid_form_passes_unchanged(validator):
    assert validator.validate(_form()) == _form()


def test_country_is_upper_cased_and_trimmed(validator):
    assert validator.validate(_form(country_code=" de ")).country_code == "DE"


def test_text_is_trimmed_before_the_length_check(validator):
    cleaned = validator.validate(_form(bio="  " + _TEXT + "\n"))

    assert cleaned.bio == _TEXT


def test_padding_does_not_count_towards_the_minimum(validator):
    with pytest.raises(InvalidProfileTextError) as error:
        validator.validate(_form(bio=" " * 50 + "x" * 150))

    assert error.value.field == "bio"


@pytest.mark.parametrize("field", ["bio", "goals_description"])
def test_text_length_bounds(validator, field):
    validator.validate(_form(**{field: "x" * 2000}))
    for bad in ["x" * 199, "x" * 2001, "", "   "]:
        with pytest.raises(InvalidProfileTextError) as error:
            validator.validate(_form(**{field: bad}))
        assert error.value.field == field


@pytest.mark.parametrize("field", ["bio", "goals_description"])
@pytest.mark.parametrize("bad", ["x" * 199 + "\x00", 123, True, None, ["x" * 200]])
def test_hostile_text_is_rejected(validator, field, bad):
    with pytest.raises(InvalidProfileTextError):
        validator.validate(_form(**{field: bad}))


@pytest.mark.parametrize("country", ["XX", "", "DEU", "D", "d3", None, 49, True])
def test_unknown_or_malformed_country_is_rejected(validator, country):
    with pytest.raises(InvalidCountryError):
        validator.validate(_form(country_code=country))


def test_timezone_must_belong_to_the_selected_country(validator):
    with pytest.raises(InvalidTimezoneError):
        validator.validate(_form(country_code="RU", timezone="Asia/Tokyo"))
    with pytest.raises(InvalidTimezoneError):
        validator.validate(_form(country_code="DE", timezone="Europe/Moscow"))


@pytest.mark.parametrize("timezone", ["", "europe/berlin", None, 1, True])
def test_malformed_timezone_is_rejected(validator, timezone):
    with pytest.raises(InvalidTimezoneError):
        validator.validate(_form(timezone=timezone))


def test_every_zone_of_the_country_is_accepted(validator):
    for zone_id in _TIMEZONES["RU"]:
        validator.validate(_form(country_code="RU", timezone=zone_id))


def test_tag_count_bounds(validator):
    validator.validate(_form(tag_ids=list(range(1, 16))))

    with pytest.raises(TooFewTagsError):
        validator.validate(_form(tag_ids=[1, 2, 3, 4]))
    with pytest.raises(TooFewTagsError):
        validator.validate(_form(tag_ids=[]))
    with pytest.raises(TooManyTagsError):
        validator.validate(_form(tag_ids=list(range(1, 17))))


def test_duplicate_tags_are_rejected_before_counting(validator):
    with pytest.raises(ProfileTagInvalidError):
        validator.validate(_form(tag_ids=[7, 7, 7, 7, 7]))
    with pytest.raises(ProfileTagInvalidError):
        validator.validate(_form(tag_ids=[1, 2, 3, 4, 5, 5]))


def test_validation_does_not_mutate_the_input(validator):
    form = _form(country_code="de", bio="  " + _TEXT)

    validator.validate(form)

    assert form.country_code == "de" and form.bio == "  " + _TEXT
