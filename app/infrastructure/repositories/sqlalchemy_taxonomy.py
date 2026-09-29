from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import (
    CategoryEntity,
    NewTagEntity,
    NewTagScopeEntity,
    RoleEntity,
    RoleFieldEntity,
    TagEntity,
    TagScopeEntity,
)
from app.domain.enums import TagStatus
from app.domain.interfaces import ITaxonomyRepository
from app.infrastructure.mappers.taxonomy_mapper import (
    map_category_model_to_category_entity,
    map_new_tag_entity_to_tag_model,
    map_new_tag_scope_entity_to_tag_scope_model,
    map_role_field_model_to_role_field_entity,
    map_role_model_to_role_entity,
    map_tag_model_to_tag_entity,
    map_tag_scope_model_to_tag_scope_entity,
)
from app.infrastructure.models import CategoryModel, RoleFieldModel, RoleModel, TagModel, TagScopeModel


class SqlAlchemyTaxonomyRepository(ITaxonomyRepository):
    def __init__(self, session: AsyncSession, suggest_limit: int) -> None:
        self._session = session
        self._suggest_limit = suggest_limit

    async def get_categories(self) -> list[CategoryEntity]:
        result = await self._session.execute(select(CategoryModel).order_by(CategoryModel.sort_order))
        return [map_category_model_to_category_entity(m) for m in result.scalars().all()]

    async def get_category_by_id(self, category_id: int) -> CategoryEntity | None:
        result = await self._session.execute(select(CategoryModel).where(CategoryModel.id == category_id))
        model = result.scalar_one_or_none()
        return map_category_model_to_category_entity(model) if model else None

    async def get_roles_by_category(self, category_id: int) -> list[RoleEntity]:
        result = await self._session.execute(
            select(RoleModel).where(RoleModel.category_id == category_id).order_by(RoleModel.sort_order)
        )
        return [map_role_model_to_role_entity(m) for m in result.scalars().all()]

    async def get_role_by_id(self, role_id: int) -> RoleEntity | None:
        result = await self._session.execute(select(RoleModel).where(RoleModel.id == role_id))
        model = result.scalar_one_or_none()
        return map_role_model_to_role_entity(model) if model else None

    async def get_role_fields_by_role(self, role_id: int) -> list[RoleFieldEntity]:
        result = await self._session.execute(
            select(RoleFieldModel)
            .where(RoleFieldModel.role_id == role_id)
            .order_by(RoleFieldModel.sort_order)
        )
        return [map_role_field_model_to_role_field_entity(m) for m in result.scalars().all()]

    async def suggest_tags(
        self, query: str, category_id: int, role_id: int | None, user_id: int
    ) -> list[TagEntity]:
        if role_id is not None:
            scope_condition = and_(
                TagScopeModel.category_id == category_id,
                or_(TagScopeModel.role_id == role_id, TagScopeModel.role_id.is_(None)),
            )
        else:
            scope_condition = and_(
                TagScopeModel.category_id == category_id,
                TagScopeModel.role_id.is_(None),
            )
        scope_exists = (
            select(TagScopeModel.id)
            .where(TagScopeModel.tag_id == TagModel.id, scope_condition)
            .exists()
        )

        result = await self._session.execute(
            select(TagModel)
            .where(
                TagModel.title.ilike(f"%{query}%"),
                scope_exists,
                or_(TagModel.status == TagStatus.APPROVED, TagModel.created_by_user_id == user_id),
            )
            .order_by(TagModel.usage_count.desc())
            .limit(self._suggest_limit)
        )
        return [map_tag_model_to_tag_entity(m) for m in result.scalars().all()]

    async def get_tag_by_slug(self, slug: str) -> TagEntity | None:
        result = await self._session.execute(select(TagModel).where(TagModel.slug == slug))
        model = result.scalar_one_or_none()
        return map_tag_model_to_tag_entity(model) if model else None

    async def create_tag(self, tag: NewTagEntity) -> TagEntity:
        model = map_new_tag_entity_to_tag_model(tag)
        self._session.add(model)
        try:
            await self._session.commit()
        except IntegrityError:
            await self._session.rollback()
            result = await self._session.execute(select(TagModel).where(TagModel.slug == tag.slug))
            return map_tag_model_to_tag_entity(result.scalar_one())
        await self._session.refresh(model)
        return map_tag_model_to_tag_entity(model)

    async def create_tag_scope(self, scope: NewTagScopeEntity) -> TagScopeEntity:
        model = map_new_tag_scope_entity_to_tag_scope_model(scope)
        self._session.add(model)
        try:
            await self._session.commit()
        except IntegrityError:
            await self._session.rollback()
            role_condition = (
                TagScopeModel.role_id == scope.role_id
                if scope.role_id is not None
                else TagScopeModel.role_id.is_(None)
            )
            result = await self._session.execute(
                select(TagScopeModel).where(
                    TagScopeModel.tag_id == scope.tag_id,
                    TagScopeModel.category_id == scope.category_id,
                    role_condition,
                )
            )
            return map_tag_scope_model_to_tag_scope_entity(result.scalar_one())
        await self._session.refresh(model)
        return map_tag_scope_model_to_tag_scope_entity(model)
