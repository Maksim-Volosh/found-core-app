import json
import logging
from collections.abc import Callable
from dataclasses import asdict
from typing import TypeVar

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.domain.entities import CategoryEntity, RoleEntity, RoleFieldEntity
from app.domain.enums import RoleFieldType
from app.domain.interfaces import ITaxonomyCacheRepository

logger = logging.getLogger(__name__)

_CATEGORIES_KEY = "taxonomy:categories"
_ROLES_KEY_TEMPLATE = "taxonomy:roles:{category_id}"
_ROLE_FIELDS_KEY_TEMPLATE = "taxonomy:role_fields:{role_id}"

T = TypeVar("T")


def _build_role_field(item: dict) -> RoleFieldEntity:
    return RoleFieldEntity(**{**item, "field_type": RoleFieldType(item["field_type"])})


class RedisTaxonomyCacheRepository(ITaxonomyCacheRepository):
    def __init__(self, redis_client: Redis, ttl_seconds: int) -> None:
        self._redis = redis_client
        self._ttl_seconds = ttl_seconds
        # One instance lives for one request: after the first Redis failure the rest of the request skips Redis
        # instead of waiting for another timeout.
        self._unavailable = False

    async def get_categories(self) -> list[CategoryEntity] | None:
        return await self._get(_CATEGORIES_KEY, lambda item: CategoryEntity(**item))

    async def set_categories(self, categories: list[CategoryEntity]) -> None:
        await self._set(_CATEGORIES_KEY, [asdict(c) for c in categories])

    async def get_roles_by_category(self, category_id: int) -> list[RoleEntity] | None:
        return await self._get(_ROLES_KEY_TEMPLATE.format(category_id=category_id), lambda item: RoleEntity(**item))

    async def set_roles_by_category(self, category_id: int, roles: list[RoleEntity]) -> None:
        await self._set(_ROLES_KEY_TEMPLATE.format(category_id=category_id), [asdict(r) for r in roles])

    async def get_role_fields_by_role(self, role_id: int) -> list[RoleFieldEntity] | None:
        return await self._get(_ROLE_FIELDS_KEY_TEMPLATE.format(role_id=role_id), _build_role_field)

    async def set_role_fields_by_role(self, role_id: int, fields: list[RoleFieldEntity]) -> None:
        await self._set(_ROLE_FIELDS_KEY_TEMPLATE.format(role_id=role_id), [asdict(f) for f in fields])

    async def _get(self, key: str, build: Callable[[dict], T]) -> list[T] | None:
        if self._unavailable:
            return None
        try:
            raw = await self._redis.get(key)
        except RedisError:
            self._unavailable = True
            logger.warning("Redis unavailable, cache read skipped for key %s", key, exc_info=True)
            return None
        if not raw:
            return None
        try:
            return [build(item) for item in json.loads(raw)]
        except (TypeError, KeyError, ValueError, RecursionError):
            # A corrupt or outdated value is a miss; the use case reloads from Postgres and overwrites it.
            logger.warning("Discarding unreadable cache value for key %s", key, exc_info=True)
            return None

    async def _set(self, key: str, items: list[dict]) -> None:
        if self._unavailable:
            return
        try:
            await self._redis.set(key, json.dumps(items), ex=self._ttl_seconds)
        except RedisError:
            self._unavailable = True
            logger.warning("Redis unavailable, cache write skipped for key %s", key, exc_info=True)
