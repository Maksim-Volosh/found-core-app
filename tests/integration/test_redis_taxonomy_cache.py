import pytest
from redis.asyncio import Redis

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
