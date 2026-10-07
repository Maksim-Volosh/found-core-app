from app.domain.entities import RoleFieldEntity
from app.domain.enums import RoleFieldType
from app.domain.exceptions import InvalidExtraAttributesError


class ExtraAttributesValidator:
    """Checks role-specific attributes against the role's `role_fields` and returns the cleaned mapping."""

    def validate(self, attributes: dict[str, str], fields: list[RoleFieldEntity]) -> dict[str, str]:
        fields_by_key = {field.key: field for field in fields}
        cleaned: dict[str, str] = {}
        for key, raw in attributes.items():
            field = fields_by_key.get(key)
            if field is None:
                raise InvalidExtraAttributesError()
            value = self._clean_value(raw)
            # An empty value means "not set": the key is dropped instead of being stored as an empty string.
            if value is None:
                continue
            self._validate_value(field, value)
            cleaned[key] = value

        for field in fields:
            if field.is_required and field.key not in cleaned:
                raise InvalidExtraAttributesError()
        return cleaned

    @staticmethod
    def _clean_value(raw: object) -> str | None:
        if raw is None:
            return None
        if type(raw) is not str or "\x00" in raw:
            raise InvalidExtraAttributesError()
        value = raw.strip()
        return value or None

    @staticmethod
    def _validate_value(field: RoleFieldEntity, value: str) -> None:
        # Only `select` fields exist so far; any other type fails closed until its rules are implemented.
        if field.field_type is not RoleFieldType.SELECT:
            raise InvalidExtraAttributesError()
        allowed = {option["value"] for option in field.options or []}
        if value not in allowed:
            raise InvalidExtraAttributesError()
