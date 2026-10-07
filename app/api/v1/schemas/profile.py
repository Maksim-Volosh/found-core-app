from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.api.v1.schemas.common import Int64Id
from app.api.v1.schemas.taxonomy import TagSchema
from app.domain.enums import ProfileStatus

# Request bounds sit above the business limits (which live in the domain validators) so
# oversized bodies are rejected before any processing.
ExtraAttributesInput = Annotated[
    dict[
        Annotated[str, Field(max_length=64)],
        Annotated[str | None, Field(max_length=128)],
    ],
    Field(max_length=32),
]


class ProfileUpdateRequest(BaseModel):
    """The editable part of a profile; also the common part of the create request."""

    model_config = ConfigDict(extra="forbid")

    country_code: str = Field(..., max_length=16)
    timezone: str = Field(..., max_length=128)
    bio: str = Field(..., max_length=4000)
    goals_description: str = Field(..., max_length=4000)
    tag_ids: list[Int64Id] = Field(..., max_length=50)
    extra_attributes: ExtraAttributesInput = Field(default_factory=dict)


class ProfileCreateRequest(ProfileUpdateRequest):
    category_id: Int64Id
    role_id: Int64Id


class ProfileSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category_id: int
    role_id: int
    country_code: str
    timezone: str
    bio: str
    goals_description: str
    extra_attributes: dict[str, str]
    status: ProfileStatus
    is_active: bool
    tags: list[TagSchema]
    created_at: datetime
    updated_at: datetime


class TextLimitsSchema(BaseModel):
    min_length: int
    max_length: int


class TagLimitsSchema(BaseModel):
    min_count: int
    max_count: int


class TimezoneSchema(BaseModel):
    id: str
    label: str
    utc_offset: str


class CountrySchema(BaseModel):
    code: str
    name: str
    timezones: list[TimezoneSchema]


class ProfileFormConfigSchema(BaseModel):
    bio: TextLimitsSchema
    goals: TextLimitsSchema
    tags: TagLimitsSchema
    countries: list[CountrySchema]
