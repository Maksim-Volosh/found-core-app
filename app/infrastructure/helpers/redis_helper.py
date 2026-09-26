from redis.asyncio import Redis

from app.core.config import settings


class RedisHelper:
    def __init__(self, url: str, socket_timeout: float) -> None:
        self.client: Redis = Redis.from_url(
            url,
            decode_responses=True,
            socket_connect_timeout=socket_timeout,
            socket_timeout=socket_timeout,
        )

    async def dispose(self) -> None:
        await self.client.aclose()


redis_helper = RedisHelper(
    url=str(settings.redis.url),
    socket_timeout=settings.redis.socket_timeout,
)
