from dataclasses import dataclass
from datetime import datetime

from app.domain.entities.taxonomy import TagEntity
from app.domain.enums import ProfileStatus


@dataclass
class ProfileFormEntity:
    """The user-editable part of a profile, as submitted by the client."""

    country_code: str
    timezone: str
    bio: str
    goals_description: str
    tag_ids: list[int]


@dataclass
class NewProfileEntity:
    user_id: int
    category_id: int
    role_id: int
    country_code: str
    timezone: str
    bio: str
    goals_description: str
    extra_attributes: dict[str, str]
    tag_ids: list[int]
    status: ProfileStatus
    created_at: datetime
    updated_at: datetime


@dataclass
class ProfileEntity:
    id: int
    user_id: int
    category_id: int
    role_id: int
    country_code: str
    timezone: str
    bio: str
    goals_description: str
    extra_attributes: dict[str, str]
    status: ProfileStatus
    created_at: datetime
    updated_at: datetime
    tags: list[TagEntity]


@dataclass
class TimezoneEntity:
    id: str
    label: str
    utc_offset: str


@dataclass
class CountryEntity:
    code: str
    name: str
    timezones: list[TimezoneEntity]
