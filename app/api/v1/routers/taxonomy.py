from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.dependencies.auth import get_current_user
from app.api.v1.mappers.taxonomy import (
    map_category_entity_to_category_schema,
    map_role_entity_to_role_schema,
    map_role_field_entity_to_role_field_schema,
    map_tag_entity_to_tag_schema,
)
from app.api.v1.schemas import (
    CategorySchema,
    CreateCustomTagRequest,
    RoleFieldSchema,
    RoleSchema,
    TagSchema,
)
from app.core.composition.container import Container
from app.core.composition.di import get_container
from app.domain.entities import UserEntity
from app.domain.exceptions import CategoryNotFoundError, RoleNotFoundError, TagTitleInvalidError

router = APIRouter(prefix="/taxonomy", tags=["Taxonomy"])


@router.get("/categories")
async def get_categories(
    container: Container = Depends(get_container),
    current_user: UserEntity = Depends(get_current_user),
) -> list[CategorySchema]:
    categories = await container.get_categories_use_case().execute()
    return [map_category_entity_to_category_schema(c) for c in categories]


@router.get("/categories/{category_id}/roles")
async def get_roles_by_category(
    category_id: int,
    container: Container = Depends(get_container),
    current_user: UserEntity = Depends(get_current_user),
) -> list[RoleSchema]:
    try:
        roles = await container.get_roles_by_category_use_case().execute(category_id)
    except CategoryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return [map_role_entity_to_role_schema(r) for r in roles]


@router.get("/roles/{role_id}/fields")
async def get_role_fields(
    role_id: int,
    container: Container = Depends(get_container),
    current_user: UserEntity = Depends(get_current_user),
) -> list[RoleFieldSchema]:
    try:
        fields = await container.get_role_fields_by_role_use_case().execute(role_id)
    except RoleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return [map_role_field_entity_to_role_field_schema(f) for f in fields]


@router.get("/tags/suggest")
async def suggest_tags(
    q: str = Query(..., min_length=1),
    category_id: int = Query(...),
    role_id: int | None = Query(None),
    container: Container = Depends(get_container),
    current_user: UserEntity = Depends(get_current_user),
) -> list[TagSchema]:
    try:
        tags = await container.suggest_tags_use_case().execute(q, category_id, role_id, current_user.id)
    except (CategoryNotFoundError, RoleNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return [map_tag_entity_to_tag_schema(t) for t in tags]


@router.post("/tags/custom")
async def create_custom_tag(
    payload: CreateCustomTagRequest,
    container: Container = Depends(get_container),
    current_user: UserEntity = Depends(get_current_user),
) -> TagSchema:
    try:
        tag = await container.create_custom_tag_use_case().execute(
            title=payload.title,
            category_id=payload.category_id,
            role_id=payload.role_id,
            user_id=current_user.id,
        )
    except (CategoryNotFoundError, RoleNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TagTitleInvalidError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return map_tag_entity_to_tag_schema(tag)
