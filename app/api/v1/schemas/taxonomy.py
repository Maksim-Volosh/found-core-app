from pydantic import BaseModel, ConfigDict, Field

from app.api.v1.schemas.common import Int64Id
from app.domain.enums import RoleFieldType, TagStatus


class CategorySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    title: str
    sort_order: int


class RoleSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category_id: int
    slug: str
    title: str
    sort_order: int


class RoleFieldSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role_id: int
    key: str
    label: str
    field_type: RoleFieldType
    options: list[dict[str, str]] | None
    is_required: bool
    is_filterable: bool
    sort_order: int


class TagSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    status: TagStatus
    usage_count: int


class CreateCustomTagRequest(BaseModel):
    # Cheap upper bound so a huge body is rejected before NFKC/casefold; the business limit lives in TagTitleValidator.
    title: str = Field(..., min_length=1, max_length=256)
    category_id: Int64Id
    role_id: Int64Id | None = None
