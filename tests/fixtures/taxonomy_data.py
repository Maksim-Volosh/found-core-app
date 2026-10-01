"""Direct ORM helpers that put a minimal taxonomy into the test database.

Deliberately not `scripts/dev_seed_taxonomy.py`: that script is the full dev
dataset (Russian labels, ~100 tags), while tests need a few rows whose ids and
scopes they can reason about.
"""

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import RoleFieldType, TagStatus
from app.domain.services import normalize_tag_title
from app.infrastructure.models import (
    CategoryModel,
    RoleFieldModel,
    RoleModel,
    TagModel,
    TagScopeModel,
)


@dataclass
class TaxonomyIds:
    tech_category_id: int
    edu_category_id: int
    engineering_role_id: int
    design_role_id: int
    study_mate_role_id: int
    grade_field_id: int


async def seed_basic_taxonomy(session: AsyncSession) -> TaxonomyIds:
    tech = CategoryModel(slug="tech_product", title="Tech & Product", sort_order=1)
    edu = CategoryModel(slug="edu_growth", title="Edu & Growth", sort_order=2)
    session.add_all([tech, edu])
    await session.flush()

    engineering = RoleModel(category_id=tech.id, slug="engineering", title="Engineering", sort_order=1)
    design = RoleModel(category_id=tech.id, slug="design", title="Design", sort_order=2)
    study_mate = RoleModel(category_id=edu.id, slug="study_mate", title="Study mate", sort_order=1)
    session.add_all([engineering, design, study_mate])
    await session.flush()

    grade = RoleFieldModel(
        role_id=engineering.id,
        key="grade",
        label="Grade",
        field_type=RoleFieldType.SELECT,
        options=[{"value": "junior", "label": "Junior"}, {"value": "middle", "label": "Middle"}],
        is_required=True,
        is_filterable=True,
        sort_order=1,
    )
    session.add(grade)
    await session.commit()

    return TaxonomyIds(
        tech_category_id=tech.id,
        edu_category_id=edu.id,
        engineering_role_id=engineering.id,
        design_role_id=design.id,
        study_mate_role_id=study_mate.id,
        grade_field_id=grade.id,
    )


async def add_tag(
    session: AsyncSession,
    title: str,
    *,
    status: TagStatus = TagStatus.APPROVED,
    created_by: int | None = None,
    usage_count: int = 0,
    scopes: list[tuple[int, int | None]] | None = None,
) -> TagModel:
    """`scopes` is a list of `(category_id, role_id)`; `role_id=None` means the whole category."""
    tag = TagModel(
        title=title,
        normalized_title=normalize_tag_title(title),
        status=status,
        created_by_user_id=created_by,
        usage_count=usage_count,
    )
    session.add(tag)
    await session.flush()
    for category_id, role_id in scopes or []:
        session.add(TagScopeModel(tag_id=tag.id, category_id=category_id, role_id=role_id))
    await session.commit()
    return tag


async def count_tags(session: AsyncSession) -> int:
    return (await session.execute(select(func.count()).select_from(TagModel))).scalar_one()


async def count_tag_scopes(session: AsyncSession) -> int:
    return (await session.execute(select(func.count()).select_from(TagScopeModel))).scalar_one()
