import json
import logging
from dataclasses import asdict

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.domain.entities import CategoryEntity, RoleEntity, RoleFieldEntity
from app.domain.enums import RoleFieldType
from app.domain.interfaces import ITaxonomyCacheRepository

logger = logging.getLogger(__name__)

_CATEGORIES_KEY = "taxonomy:categories"
_ROLES_KEY_TEMPLATE = "taxonomy:roles:{category_id}"
_ROLE_FIELDS_KEY_TEMPLATE = "taxonomy:role_fields:{role_id}"


class RedisTaxonomyCacheRepository(ITaxonomyCacheRepository):
    def __init__(self, redis_client: Redis, ttl_seconds: int) -> None:
        self._redis = redis_client
        self._ttl_seconds = ttl_seconds

    async def get_categories(self) -> list[CategoryEntity] | None:
        items = await self._get(_CATEGORIES_KEY)
        if items is None:
            return None
        return [CategoryEntity(**item) for item in items]

    async def set_categories(self, categories: list[CategoryEntity]) -> None:
        await self._set(_CATEGORIES_KEY, [asdict(c) for c in categories])

    async def get_roles_by_category(self, category_id: int) -> list[RoleEntity] | None:
        items = await self._get(_ROLES_KEY_TEMPLATE.format(category_id=category_id))
        if items is None:
            return None
        return [RoleEntity(**item) for item in items]

    async def set_roles_by_category(self, category_id: int, roles: list[RoleEntity]) -> None:
        await self._set(_ROLES_KEY_TEMPLATE.format(category_id=category_id), [asdict(r) for r in roles])

    async def get_role_fields_by_role(self, role_id: int) -> list[RoleFieldEntity] | None:
        items = await self._get(_ROLE_FIELDS_KEY_TEMPLATE.format(role_id=role_id))
        if items is None:
            return None
        return [RoleFieldEntity(**{**item, "field_type": RoleFieldType(item["field_type"])}) for item in items]

    async def set_role_fields_by_role(self, role_id: int, fields: list[RoleFieldEntity]) -> None:
        await self._set(_ROLE_FIELDS_KEY_TEMPLATE.format(role_id=role_id), [asdict(f) for f in fields])

    async def _get(self, key: str) -> list[dict] | None:
        try:
            raw = await self._redis.get(key)
        except RedisError:
            logger.warning("Redis unavailable, cache read skipped for key %s", key, exc_info=True)
            return None
        return json.loads(raw) if raw else None

    async def _set(self, key: str, items: list[dict]) -> None:
        try:
            await self._redis.set(key, json.dumps(items), ex=self._ttl_seconds)
        except RedisError:
            logger.warning("Redis unavailable, cache write skipped for key %s", key, exc_info=True)
