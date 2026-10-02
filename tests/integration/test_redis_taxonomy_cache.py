import asyncio
import time

import pytest
from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError

from app.domain.entities import CategoryEntity, RoleEntity, RoleFieldEntity
from app.domain.enums import RoleFieldType
from app.infrastructure.repositories.redis_taxonomy_cache import RedisTaxonomyCacheRepository

TTL = 120

CATEGORIES = [
    CategoryEntity(id=1, slug="tech_product", title="Tech & Product", sort_order=1),
    CategoryEntity(id=2, slug="edu_growth", title="Edu & Growth", sort_order=2),
]
ROLES = [RoleEntity(id=10, category_id=1, slug="engineering", title="Engineering", sort_order=1)]
FIELDS = [
    RoleFieldEntity(
        id=100,
        role_id=10,
        key="grade",
        label="Grade",
        field_type=RoleFieldType.SELECT,
        options=[{"value": "junior", "label": "Junior"}],
        is_required=True,
        is_filterable=True,
        sort_order=1,
    ),
    RoleFieldEntity(
        id=101,
        role_id=10,
        key="bio",
        label="Bio",
        field_type=RoleFieldType.TEXT,
        options=None,
        is_required=False,
        is_filterable=False,
    ),
]


@pytest.fixture
def cache(redis_client: Redis) -> RedisTaxonomyCacheRepository:
    return RedisTaxonomyCacheRepository(redis_client=redis_client, ttl_seconds=TTL)


async def test_miss_returns_none_for_every_getter(cache):
    assert await cache.get_categories() is None
    assert await cache.get_roles_by_category(1) is None
    assert await cache.get_role_fields_by_role(10) is None


async def test_categories_round_trip(cache):
    await cache.set_categories(CATEGORIES)

    assert await cache.get_categories() == CATEGORIES


async def test_roles_round_trip_is_keyed_by_category(cache):
    await cache.set_roles_by_category(1, ROLES)

    assert await cache.get_roles_by_category(1) == ROLES
    assert await cache.get_roles_by_category(2) is None


async def test_role_fields_round_trip_rebuilds_the_enum_and_keeps_options(cache):
    await cache.set_role_fields_by_role(10, FIELDS)

    loaded = await cache.get_role_fields_by_role(10)

    assert loaded == FIELDS
    assert loaded[0].field_type is RoleFieldType.SELECT
    assert loaded[0].options == [{"value": "junior", "label": "Junior"}]
    assert loaded[1].options is None


async def test_empty_list_is_cached_as_a_hit_not_a_miss(cache):
    # An empty role-field list is a legitimate cached value; it must not look like a miss.
    await cache.set_role_fields_by_role(10, [])

    assert await cache.get_role_fields_by_role(10) == []


async def test_keys_have_the_documented_names_and_a_ttl(cache, redis_client):
    await cache.set_categories(CATEGORIES)
    await cache.set_roles_by_category(1, ROLES)
    await cache.set_role_fields_by_role(10, FIELDS)

    for key in ("taxonomy:categories", "taxonomy:roles:1", "taxonomy:role_fields:10"):
        assert await redis_client.exists(key) == 1
        assert 0 < await redis_client.ttl(key) <= TTL


@pytest.mark.parametrize(
    "stored",
    [
        "{not json",
        "null",
        "42",
        '"text"',
        '{"id": 1}',  # an object instead of a list
        "[1, 2]",
        '[{"id": 1, "slug": "x"}]',  # outdated shape: fields missing
        '[{"id": 1, "slug": "x", "title": "T", "sort_order": 1, "removed_field": 5}]',  # unknown field
        "[" * 100_000,  # blows the JSON recursion limit
    ],
)
async def test_unreadable_categories_value_is_a_miss_not_an_error(cache, redis_client, stored):
    await redis_client.set("taxonomy:categories", stored)

    assert await cache.get_categories() is None


async def test_unknown_enum_value_in_role_fields_is_a_miss(cache, redis_client):
    await cache.set_role_fields_by_role(10, FIELDS)
    raw = await redis_client.get("taxonomy:role_fields:10")
    await redis_client.set("taxonomy:role_fields:10", raw.replace('"select"', '"hologram"'))

    assert await cache.get_role_fields_by_role(10) is None


async def test_a_corrupt_value_is_overwritten_by_the_next_write(cache, redis_client):
    await redis_client.set("taxonomy:categories", "{not json")
    assert await cache.get_categories() is None

    await cache.set_categories(CATEGORIES)

    assert await cache.get_categories() == CATEGORIES


class _CountingFailingRedis:
    """Stands in for a Redis client whose server is down."""

    def __init__(self) -> None:
        self.calls = 0

    async def get(self, key):
        self.calls += 1
        raise RedisConnectionError("down")

    async def set(self, key, value, ex=None):
        self.calls += 1
        raise RedisConnectionError("down")


async def test_after_the_first_redis_error_the_rest_of_the_request_skips_the_network():
    failing = _CountingFailingRedis()
    cache = RedisTaxonomyCacheRepository(redis_client=failing, ttl_seconds=TTL)

    assert await cache.get_categories() is None
    await cache.set_categories(CATEGORIES)
    assert await cache.get_roles_by_category(1) is None
    await cache.set_roles_by_category(1, ROLES)

    assert failing.calls == 1


async def test_a_new_instance_tries_redis_again():
    failing = _CountingFailingRedis()

    await RedisTaxonomyCacheRepository(redis_client=failing, ttl_seconds=TTL).get_categories()
    await RedisTaxonomyCacheRepository(redis_client=failing, ttl_seconds=TTL).get_categories()

    assert failing.calls == 2


async def test_a_redis_that_accepts_connections_but_never_answers_does_not_hang_the_request():
    handlers: list[asyncio.Task] = []

    async def _accept_and_stay_silent(reader, writer):
        handlers.append(asyncio.current_task())
        await asyncio.sleep(30)

    server = await asyncio.start_server(_accept_and_stay_silent, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    client = Redis.from_url(
        f"redis://127.0.0.1:{port}/0", decode_responses=True, socket_connect_timeout=0.3, socket_timeout=0.3
    )
    cache = RedisTaxonomyCacheRepository(redis_client=client, ttl_seconds=TTL)
    try:
        assert await asyncio.wait_for(cache.get_categories(), timeout=10) is None

        started = time.monotonic()
        await cache.set_categories(CATEGORIES)
        # The failed read already marked Redis unavailable, so the write must not wait for a second timeout.
        assert time.monotonic() - started < 0.1
    finally:
        await client.aclose()
        server.close()
        for handler in handlers:
            handler.cancel()
        await asyncio.gather(*handlers, return_exceptions=True)


async def test_redis_outage_reads_as_a_miss_and_writes_do_not_raise():
    dead_client = Redis.from_url(
        "redis://localhost:1/0", decode_responses=True, socket_connect_timeout=0.5, socket_timeout=0.5
    )
    cache = RedisTaxonomyCacheRepository(redis_client=dead_client, ttl_seconds=TTL)
    try:
        assert await cache.get_categories() is None
        await cache.set_categories(CATEGORIES)
        assert await cache.get_roles_by_category(1) is None
        await cache.set_roles_by_category(1, ROLES)
        assert await cache.get_role_fields_by_role(10) is None
        await cache.set_role_fields_by_role(10, FIELDS)
    finally:
        await dead_client.aclose()
