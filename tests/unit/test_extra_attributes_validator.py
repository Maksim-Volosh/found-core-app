import pytest

from app.domain.entities import RoleFieldEntity
from app.domain.enums import RoleFieldType
from app.domain.exceptions import InvalidExtraAttributesError
from app.domain.services import ExtraAttributesValidator


_DEFAULT_OPTIONS = object()


def _field(key, *, required=False, field_type=RoleFieldType.SELECT, options=_DEFAULT_OPTIONS) -> RoleFieldEntity:
    if options is _DEFAULT_OPTIONS:
        options = [{"value": "a", "label": "A"}, {"value": "b", "label": "B"}]
    return RoleFieldEntity(
        id=1,
        role_id=1,
        key=key,
        label=key,
        field_type=field_type,
        options=options,
        is_required=required,
        is_filterable=True,
    )


@pytest.fixture
def validator() -> ExtraAttributesValidator:
    return ExtraAttributesValidator()


@pytest.fixture
def fields() -> list[RoleFieldEntity]:
    return [_field("grade", required=True), _field("workload")]


def test_valid_attributes_pass(validator, fields):
    assert validator.validate({"grade": "a", "workload": "b"}, fields) == {"grade": "a", "workload": "b"}


def test_optional_attribute_may_be_absent(validator, fields):
    assert validator.validate({"grade": "a"}, fields) == {"grade": "a"}


def test_missing_required_attribute_is_rejected(validator, fields):
    with pytest.raises(InvalidExtraAttributesError):
        validator.validate({"workload": "a"}, fields)
    with pytest.raises(InvalidExtraAttributesError):
        validator.validate({}, fields)


@pytest.mark.parametrize("empty", ["", "   ", None])
def test_empty_optional_value_is_dropped(validator, fields, empty):
    assert validator.validate({"grade": "a", "workload": empty}, fields) == {"grade": "a"}


@pytest.mark.parametrize("empty", ["", "  ", None])
def test_empty_required_value_counts_as_missing(validator, fields, empty):
    with pytest.raises(InvalidExtraAttributesError):
        validator.validate({"grade": empty}, fields)


def test_value_is_trimmed(validator, fields):
    assert validator.validate({"grade": " a "}, fields) == {"grade": "a"}


def test_unknown_key_is_rejected(validator, fields):
    with pytest.raises(InvalidExtraAttributesError):
        validator.validate({"grade": "a", "stack": "a"}, fields)


def test_value_outside_options_is_rejected(validator, fields):
    with pytest.raises(InvalidExtraAttributesError):
        validator.validate({"grade": "c"}, fields)
    with pytest.raises(InvalidExtraAttributesError):
        validator.validate({"grade": "A"}, fields)


@pytest.mark.parametrize("bad", [1, True, ["a"], {"value": "a"}, "a\x00"])
def test_non_string_or_nul_values_are_rejected(validator, fields, bad):
    with pytest.raises(InvalidExtraAttributesError):
        validator.validate({"grade": bad}, fields)


def test_select_without_options_accepts_nothing(validator):
    fields = [_field("grade", options=None)]

    with pytest.raises(InvalidExtraAttributesError):
        validator.validate({"grade": "a"}, fields)


def test_unsupported_field_type_fails_closed(validator):
    fields = [_field("years", field_type=RoleFieldType.NUMBER)]

    with pytest.raises(InvalidExtraAttributesError):
        validator.validate({"years": "3"}, fields)


def test_role_without_fields_accepts_only_empty_attributes(validator):
    assert validator.validate({}, []) == {}
    with pytest.raises(InvalidExtraAttributesError):
        validator.validate({"grade": "a"}, [])


def test_validation_does_not_mutate_the_input(validator, fields):
    attributes = {"grade": " a ", "workload": ""}

    validator.validate(attributes, fields)

    assert attributes == {"grade": " a ", "workload": ""}
