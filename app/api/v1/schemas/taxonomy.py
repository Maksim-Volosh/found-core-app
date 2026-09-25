from pydantic import BaseModel, ConfigDict, Field

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
    slug: str
    title: str
    status: TagStatus
    usage_count: int


class CreateCustomTagRequest(BaseModel):
    title: str = Field(..., min_length=1)
    category_id: int
    role_id: int | None = None
