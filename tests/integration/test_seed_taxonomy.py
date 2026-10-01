"""Runs the real dev seed script against the test database."""

import pytest
from sqlalchemy import func, select

from app.core.config import settings
from app.domain.enums import TagStatus
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


def test_every_seeded_title_would_also_be_accepted_from_a_user():
    validator = TagTitleValidator(
        min_length=settings.taxonomy.tag_title_min_length,
        max_length=settings.taxonomy.tag_title_max_length,
        pattern=settings.taxonomy.tag_title_allowed_pattern,
    )

    for titles in TAGS_BY_ROLE.values():
        for title in titles:
            validator.validate(title)
