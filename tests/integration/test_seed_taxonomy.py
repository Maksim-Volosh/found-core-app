"""Runs the real dev seed script against the test database."""

import pytest
from sqlalchemy import func, select

from app.core.config import settings
from app.domain.enums import RoleFieldType, TagStatus
from app.domain.services import TagTitleValidator, normalize_tag_title
from app.infrastructure.models import CategoryModel, RoleFieldModel, RoleModel, TagModel, TagScopeModel
from scripts.dev_seed_taxonomy import CATEGORIES, ROLE_FIELDS, ROLES, TAGS_BY_ROLE, main


async def _count(session, model) -> int:
    return (await session.execute(select(func.count()).select_from(model))).scalar_one()


async def _counts(session) -> dict[str, int]:
    return {
        m.__tablename__: await _count(session, m)
        for m in (CategoryModel, RoleModel, RoleFieldModel, TagModel, TagScopeModel)
    }


@pytest.fixture
async def seeded(session) -> dict[str, int]:
    await main()
    return await _counts(session)


def _unique_normalized_titles() -> set[str]:
    return {normalize_tag_title(t) for titles in TAGS_BY_ROLE.values() for t in titles}


def _unique_scopes() -> set[tuple[str, str]]:
    return {(role, normalize_tag_title(t)) for role, titles in TAGS_BY_ROLE.items() for t in titles}


async def test_seed_creates_every_row_from_the_source_data(seeded):
    assert seeded["categories"] == len(CATEGORIES)
    assert seeded["roles"] == len(ROLES)
    assert seeded["role_fields"] == len(ROLE_FIELDS)
    assert seeded["tags"] == len(_unique_normalized_titles())
    assert seeded["tag_scopes"] == len(_unique_scopes())


async def test_seed_is_idempotent(session, seeded):
    await main()

    assert await _counts(session) == seeded


async def test_seeded_tags_are_approved_and_have_no_author(session, seeded):
    rows = (await session.execute(select(TagModel.status, TagModel.created_by_user_id))).all()

    assert {r.status for r in rows} == {TagStatus.APPROVED}
    assert {r.created_by_user_id for r in rows} == {None}


async def test_every_seeded_tag_has_at_least_one_scope(session, seeded):
    unscoped = (
        await session.execute(
            select(func.count())
            .select_from(TagModel)
            .where(~select(TagScopeModel.id).where(TagScopeModel.tag_id == TagModel.id).exists())
        )
    ).scalar_one()

    assert unscoped == 0


def test_seed_source_data_is_internally_consistent():
    role_slugs = {r["slug"] for r in ROLES}
    category_slugs = {c["slug"] for c in CATEGORIES}

    assert {r["category_slug"] for r in ROLES} <= category_slugs
    assert {f["role_slug"] for f in ROLE_FIELDS} <= role_slugs
    assert set(TAGS_BY_ROLE) <= role_slugs
    assert len(role_slugs) == len(ROLES)  # slugs are unique, the seed maps roles by slug alone


def test_every_select_field_has_usable_options():
    for field in ROLE_FIELDS:
        if field["field_type"] is not RoleFieldType.SELECT:
            continue
        where = f"{field['role_slug']}.{field['key']}"
        options = field["options"]

        assert options, where
        assert all(set(o) == {"value", "label"} for o in options), where
        assert all(o["value"] and o["label"] for o in options), where
        values = [o["value"] for o in options]
        assert len(values) == len(set(values)), where


def test_field_keys_are_unique_within_a_role():
    keys = [(f["role_slug"], f["key"]) for f in ROLE_FIELDS]

    assert len(keys) == len(set(keys))


def test_every_role_has_format_and_its_category_availability_field():
    category_of = {r["slug"]: r["category_slug"] for r in ROLES}
    availability_key = {"tech_product": "workload", "edu_growth": "frequency"}

    for role_slug, category_slug in category_of.items():
        keys = {f["key"] for f in ROLE_FIELDS if f["role_slug"] == role_slug}

        assert "format" in keys, role_slug
        assert availability_key[category_slug] in keys, role_slug


async def test_seed_clears_stale_taxonomy_cache_and_keeps_foreign_keys(redis_client):
    await redis_client.set("taxonomy:categories", "stale")
    await redis_client.set("taxonomy:roles:1", "stale")
    await redis_client.set("unrelated:key", "keep")

    await main()

    assert await redis_client.exists("taxonomy:categories", "taxonomy:roles:1") == 0
    assert await redis_client.get("unrelated:key") == "keep"


def test_every_seeded_title_would_also_be_accepted_from_a_user():
    validator = TagTitleValidator(
        min_length=settings.taxonomy.tag_title_min_length,
        max_length=settings.taxonomy.tag_title_max_length,
        pattern=settings.taxonomy.tag_title_allowed_pattern,
    )

    for titles in TAGS_BY_ROLE.values():
        for title in titles:
            validator.validate(title)


def test_every_role_has_enough_distinct_tags_to_build_a_profile():
    for role_slug, titles in TAGS_BY_ROLE.items():
        distinct = {normalize_tag_title(t) for t in titles}

        assert len(distinct) == len(titles), f"{role_slug} has duplicate tags"
        assert len(distinct) >= settings.profile.tags_min_count, f"{role_slug} has too few tags"

    assert set(TAGS_BY_ROLE) == {r["slug"] for r in ROLES}
