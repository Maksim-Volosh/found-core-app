from app.api.v1.schemas import CategorySchema, RoleFieldSchema, RoleSchema, TagSchema
from app.domain.entities import CategoryEntity, RoleEntity, RoleFieldEntity, TagEntity


def map_category_entity_to_category_schema(entity: CategoryEntity) -> CategorySchema:
    return CategorySchema(
        id=entity.id,
        slug=entity.slug,
        title=entity.title,
        sort_order=entity.sort_order,
    )


def map_role_entity_to_role_schema(entity: RoleEntity) -> RoleSchema:
    return RoleSchema(
        id=entity.id,
        category_id=entity.category_id,
        slug=entity.slug,
        title=entity.title,
        sort_order=entity.sort_order,
    )


def map_role_field_entity_to_role_field_schema(entity: RoleFieldEntity) -> RoleFieldSchema:
    return RoleFieldSchema(
        id=entity.id,
        role_id=entity.role_id,
        key=entity.key,
        label=entity.label,
        field_type=entity.field_type,
        options=entity.options,
        is_required=entity.is_required,
        is_filterable=entity.is_filterable,
        sort_order=entity.sort_order,
    )


def map_tag_entity_to_tag_schema(entity: TagEntity) -> TagSchema:
    return TagSchema(
        id=entity.id,
        slug=entity.slug,
        title=entity.title,
        status=entity.status,
        usage_count=entity.usage_count,
    )
