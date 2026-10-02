import pytest

from app.core.config import TaxonomyConfig
from app.domain.exceptions import TagTitleInvalidError
from app.domain.services import TagTitleValidator

_config = TaxonomyConfig()


@pytest.fixture
def validator() -> TagTitleValidator:
    return TagTitleValidator(
        min_length=_config.tag_title_min_length,
        max_length=_config.tag_title_max_length,
        pattern=_config.tag_title_allowed_pattern,
    )


@pytest.mark.parametrize(
    "title",
    ["C", "R", "Go", "C++", "C#", ".NET", "Node.js", "CI/CD", "UI/UX", "front-end", "Питон", "Machine Learning"],
)
def test_accepts_valid_titles(validator, title):
    validator.validate(title)


@pytest.mark.parametrize(
    "title",
    ["", "<script>", "a@b", "tag!", "rocket \U0001f680", "a;b", "a\\b"],
)
def test_rejects_invalid_titles(validator, title):
    with pytest.raises(TagTitleInvalidError):
        validator.validate(title)


@pytest.mark.parametrize("title", ["...", "+++", "-", "_", "#", "+ +", "./", "- - -", "___"])
def test_rejects_titles_without_a_letter_or_digit(validator, title):
    # These match the allowed-character pattern but carry no content at all.
    with pytest.raises(TagTitleInvalidError):
        validator.validate(title)


@pytest.mark.parametrize("title", ["C", "1", "3D", "C++", ".NET", "-a", "a_"])
def test_a_single_letter_or_digit_is_enough(validator, title):
    validator.validate(title)


def test_length_boundary(validator):
    validator.validate("a" * _config.tag_title_max_length)
    with pytest.raises(TagTitleInvalidError):
        validator.validate("a" * (_config.tag_title_max_length + 1))


def test_respects_custom_min_length():
    strict = TagTitleValidator(min_length=3, max_length=10, pattern=_config.tag_title_allowed_pattern)

    with pytest.raises(TagTitleInvalidError):
        strict.validate("ab")
    strict.validate("abc")


def test_pattern_must_match_the_whole_title():
    # fullmatch, not search: a valid prefix must not let an invalid tail through.
    only_digits = TagTitleValidator(min_length=1, max_length=10, pattern=r"\d+")

    only_digits.validate("123")
    with pytest.raises(TagTitleInvalidError):
        only_digits.validate("123abc")
