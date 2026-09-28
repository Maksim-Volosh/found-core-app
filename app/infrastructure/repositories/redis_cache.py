import json
import logging
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.domain.interfaces import ICacheRepository

logger = logging.getLogger(__name__)


class RedisCacheRepository(ICacheRepository):
    def __init__(self, redis_client: Redis) -> None:
        self._redis = redis_client

    async def get(self, key: str) -> Any | None:
        try:
            raw = await self._redis.get(key)
        except RedisError:
            logger.warning("Redis unavailable, cache read skipped for key %s", key, exc_info=True)
            return None
        return json.loads(raw) if raw else None

    async def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        try:
            await self._redis.set(key, json.dumps(value), ex=ttl_seconds)
        except RedisError:
            logger.warning("Redis unavailable, cache write skipped for key %s", key, exc_info=True)
