from collections.abc import Collection, Mapping
from dataclasses import replace

from app.domain.entities import ProfileFormEntity
from app.domain.exceptions import (
    InvalidCountryError,
    InvalidProfileTextError,
    InvalidTimezoneError,
    ProfileTagInvalidError,
    TooFewTagsError,
    TooManyTagsError,
)


class ProfileFormValidator:
    """Validates the common profile fields and returns a cleaned copy (trimmed text, upper-case country)."""

    def __init__(
        self,
        *,
        bio_min_length: int,
        bio_max_length: int,
        goals_min_length: int,
        goals_max_length: int,
        tags_min_count: int,
        tags_max_count: int,
        timezones_by_country: Mapping[str, Collection[str]],
    ) -> None:
        self._bio_limits = (bio_min_length, bio_max_length)
        self._goals_limits = (goals_min_length, goals_max_length)
        self._tags_min_count = tags_min_count
        self._tags_max_count = tags_max_count
        self._timezones_by_country = timezones_by_country

    def validate(self, form: ProfileFormEntity) -> ProfileFormEntity:
        country_code = self._clean_country_code(form.country_code)
        self._validate_timezone(country_code, form.timezone)
        bio = self._clean_text("bio", form.bio, self._bio_limits)
        goals_description = self._clean_text("goals_description", form.goals_description, self._goals_limits)
        self._validate_tag_ids(form.tag_ids)
        return replace(
            form,
            country_code=country_code,
            bio=bio,
            goals_description=goals_description,
        )

    def _clean_country_code(self, raw: str) -> str:
        if type(raw) is not str:
            raise InvalidCountryError()
        country_code = raw.strip().upper()
        if country_code not in self._timezones_by_country:
            raise InvalidCountryError()
        return country_code

    def _validate_timezone(self, country_code: str, timezone: str) -> None:
        if type(timezone) is not str or timezone not in self._timezones_by_country[country_code]:
            raise InvalidTimezoneError()

    @staticmethod
    def _clean_text(field: str, raw: str, limits: tuple[int, int]) -> str:
        # Postgres rejects NUL characters in text columns, so they must never get that far.
        if type(raw) is not str or "\x00" in raw:
            raise InvalidProfileTextError(field)
        text = raw.strip()
        if not limits[0] <= len(text) <= limits[1]:
            raise InvalidProfileTextError(field)
        return text

    def _validate_tag_ids(self, tag_ids: list[int]) -> None:
        # Duplicates are checked before counting so that five copies of one tag do not pass the minimum.
        if len(set(tag_ids)) != len(tag_ids):
            raise ProfileTagInvalidError()
        if len(tag_ids) < self._tags_min_count:
            raise TooFewTagsError()
        if len(tag_ids) > self._tags_max_count:
            raise TooManyTagsError()
