from app.domain.entities import (
    CategoryEntity,
    NewTagEntity,
    NewTagScopeEntity,
    RoleEntity,
    RoleFieldEntity,
    TagEntity,
    TagScopeEntity,
)
from app.infrastructure.models import CategoryModel, RoleFieldModel, RoleModel, TagModel, TagScopeModel


def map_category_model_to_category_entity(model: CategoryModel) -> CategoryEntity:
    return CategoryEntity(
        id=model.id,
        slug=model.slug,
        title=model.title,
        sort_order=model.sort_order,
    )


def map_role_model_to_role_entity(model: RoleModel) -> RoleEntity:
    return RoleEntity(
        id=model.id,
        category_id=model.category_id,
        slug=model.slug,
        title=model.title,
        sort_order=model.sort_order,
    )


def map_role_field_model_to_role_field_entity(model: RoleFieldModel) -> RoleFieldEntity:
    return RoleFieldEntity(
        id=model.id,
        role_id=model.role_id,
        key=model.key,
        label=model.label,
        field_type=model.field_type,
        options=model.options,
        is_required=model.is_required,
        is_filterable=model.is_filterable,
        sort_order=model.sort_order,
    )


def map_tag_model_to_tag_entity(model: TagModel) -> TagEntity:
    return TagEntity(
        id=model.id,
        slug=model.slug,
        title=model.title,
        status=model.status,
        created_by_user_id=model.created_by_user_id,
        usage_count=model.usage_count,
    )


def map_new_tag_entity_to_tag_model(entity: NewTagEntity) -> TagModel:
    return TagModel(
        slug=entity.slug,
        title=entity.title,
        status=entity.status,
        created_by_user_id=entity.created_by_user_id,
    )


def map_tag_scope_model_to_tag_scope_entity(model: TagScopeModel) -> TagScopeEntity:
    return TagScopeEntity(
        id=model.id,
        tag_id=model.tag_id,
        category_id=model.category_id,
        role_id=model.role_id,
    )


def map_new_tag_scope_entity_to_tag_scope_model(entity: NewTagScopeEntity) -> TagScopeModel:
    return TagScopeModel(
        tag_id=entity.tag_id,
        category_id=entity.category_id,
        role_id=entity.role_id,
    )
