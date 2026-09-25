import json
import logging
from dataclasses import asdict

from redis.asyncio import Redis
from redis.exceptions import RedisError
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
from app.domain.enums import RoleFieldType, TagStatus
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

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 21600
SUGGEST_LIMIT = 20


class SqlAlchemyTaxonomyRepository(ITaxonomyRepository):
    def __init__(self, session: AsyncSession, redis_client: Redis) -> None:
        self._session = session
        self._redis = redis_client

    async def get_categories(self) -> list[CategoryEntity]:
        key = "taxonomy:categories"
        cached = await self._cache_get(key)
        if cached is not None:
            return [CategoryEntity(**item) for item in cached]

        result = await self._session.execute(select(CategoryModel).order_by(CategoryModel.sort_order))
        entities = [map_category_model_to_category_entity(m) for m in result.scalars().all()]
        await self._cache_set(key, [asdict(e) for e in entities])
        return entities

    async def get_category_by_id(self, category_id: int) -> CategoryEntity | None:
        result = await self._session.execute(select(CategoryModel).where(CategoryModel.id == category_id))
        model = result.scalar_one_or_none()
        return map_category_model_to_category_entity(model) if model else None

    async def get_roles_by_category(self, category_id: int) -> list[RoleEntity]:
        key = f"taxonomy:roles:{category_id}"
        cached = await self._cache_get(key)
        if cached is not None:
            return [RoleEntity(**item) for item in cached]

        result = await self._session.execute(
            select(RoleModel).where(RoleModel.category_id == category_id).order_by(RoleModel.sort_order)
        )
        entities = [map_role_model_to_role_entity(m) for m in result.scalars().all()]
        await self._cache_set(key, [asdict(e) for e in entities])
        return entities

    async def get_role_by_id(self, role_id: int) -> RoleEntity | None:
        result = await self._session.execute(select(RoleModel).where(RoleModel.id == role_id))
        model = result.scalar_one_or_none()
        return map_role_model_to_role_entity(model) if model else None

    async def get_role_fields_by_role(self, role_id: int) -> list[RoleFieldEntity]:
        key = f"taxonomy:role_fields:{role_id}"
        cached = await self._cache_get(key)
        if cached is not None:
            return [
                RoleFieldEntity(**{**item, "field_type": RoleFieldType(item["field_type"])}) for item in cached
            ]

        result = await self._session.execute(
            select(RoleFieldModel)
            .where(RoleFieldModel.role_id == role_id)
            .order_by(RoleFieldModel.sort_order)
        )
        entities = [map_role_field_model_to_role_field_entity(m) for m in result.scalars().all()]
        await self._cache_set(key, [asdict(e) for e in entities])
        return entities

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
            .limit(SUGGEST_LIMIT)
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

    async def _cache_get(self, key: str) -> list[dict] | None:
        try:
            raw = await self._redis.get(key)
        except RedisError:
            logger.warning("Redis unavailable, falling back to Postgres for key %s", key, exc_info=True)
            return None
        return json.loads(raw) if raw else None

    async def _cache_set(self, key: str, value: list[dict]) -> None:
        try:
            await self._redis.set(key, json.dumps(value), ex=CACHE_TTL_SECONDS)
        except RedisError:
            logger.warning("Redis unavailable, skipping cache write for key %s", key, exc_info=True)
