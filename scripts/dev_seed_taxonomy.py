"""Dev-only: fills the categories/roles/role_fields/tags/tag_scopes tables
with the base data from the spec (section 3) and the role schemas. Idempotent —
re-running it creates no duplicates (ON CONFLICT DO NOTHING on the unique fields).

Requires the schema to exist: run `alembic upgrade head` first.

Usage:
    python -m scripts.dev_seed_taxonomy
"""

import asyncio
import logging

from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domain.enums import RoleFieldType, TagStatus
from app.domain.services import normalize_tag_title
from app.infrastructure.helpers import db_helper
from app.infrastructure.models import CategoryModel, RoleFieldModel, RoleModel, TagModel, TagScopeModel

logger = logging.getLogger(__name__)

CATEGORIES = [
    {"slug": "tech_product", "title": "Tech & Product", "sort_order": 0},
    {"slug": "edu_growth", "title": "Edu & Growth", "sort_order": 1},
]

ROLES = [
    {"category_slug": "tech_product", "slug": "founder", "title": "Фаундер", "sort_order": 0},
    {
        "category_slug": "tech_product",
        "slug": "product_project",
        "title": "Продакт/Проджект-менеджер",
        "sort_order": 1,
    },
    {"category_slug": "tech_product", "slug": "engineering", "title": "Инженер", "sort_order": 2},
    {"category_slug": "tech_product", "slug": "design", "title": "Дизайнер", "sort_order": 3},
    {"category_slug": "tech_product", "slug": "marketing", "title": "Маркетолог", "sort_order": 4},
    {"category_slug": "tech_product", "slug": "sales_bizdev", "title": "Sales/BizDev", "sort_order": 5},
    {
        "category_slug": "tech_product",
        "slug": "finance_legal",
        "title": "Финансы и право",
        "sort_order": 6,
    },
    {
        "category_slug": "edu_growth",
        "slug": "study_mate",
        "title": "Учебный партнёр",
        "sort_order": 0,
    },
    {
        "category_slug": "edu_growth",
        "slug": "language_buddy",
        "title": "Языковой партнёр",
        "sort_order": 1,
    },
    {
        "category_slug": "edu_growth",
        "slug": "pet_project_partner",
        "title": "Пет-проект/хакатон",
        "sort_order": 2,
    },
    {
        "category_slug": "edu_growth",
        "slug": "mentor_mentee",
        "title": "Ментор/менти",
        "sort_order": 3,
    },
]

_GRADE_OPTIONS = [
    {"value": "junior", "label": "Junior"},
    {"value": "middle", "label": "Middle"},
    {"value": "senior", "label": "Senior"},
    {"value": "lead", "label": "Lead"},
]
_WORKLOAD_FIELD = {
    "key": "workload",
    "label": "Загрузка",
    "field_type": RoleFieldType.SELECT,
    "options": [
        {"value": "equity", "label": "За долю"},
        {"value": "part_time", "label": "Part-time"},
        {"value": "full_time", "label": "Full-time"},
    ],
    "is_required": True,
    "is_filterable": True,
}
_TECH_FORMAT_FIELD = {
    "key": "format",
    "label": "Формат работы",
    "field_type": RoleFieldType.SELECT,
    "options": [
        {"value": "remote", "label": "Удалённо"},
        {"value": "hybrid", "label": "Гибрид"},
        {"value": "office", "label": "Офис"},
    ],
    "is_required": True,
    "is_filterable": True,
}
_EDU_FREQUENCY_FIELD = {
    "key": "frequency",
    "label": "Частота",
    "field_type": RoleFieldType.SELECT,
    "options": [
        {"value": "daily", "label": "Каждый день"},
        {"value": "few_times_a_week", "label": "Несколько раз в неделю"},
        {"value": "weekly", "label": "Раз в неделю"},
        {"value": "occasionally", "label": "От случая к случаю"},
    ],
    "is_required": True,
    "is_filterable": True,
}
_EDU_FORMAT_FIELD = {
    "key": "format",
    "label": "Формат",
    "field_type": RoleFieldType.SELECT,
    "options": [
        {"value": "online", "label": "Онлайн"},
        {"value": "offline", "label": "Оффлайн"},
        {"value": "both", "label": "Онлайн и оффлайн"},
    ],
    "is_required": True,
    "is_filterable": True,
}


def _with_defaults(role_slug: str, fields: list[dict]) -> list[dict]:
    return [{**f, "role_slug": role_slug, "sort_order": i} for i, f in enumerate(fields)]


ROLE_FIELDS: list[dict] = [
    *_with_defaults(
        "founder",
        [
            {
                "key": "project_stage",
                "label": "Стадия проекта",
                "field_type": RoleFieldType.SELECT,
                "options": [
                    {"value": "idea", "label": "Идея"},
                    {"value": "mvp", "label": "MVP"},
                    {"value": "active_project", "label": "Действующий проект"},
                    {"value": "revenue", "label": "Есть выручка"},
                    {"value": "investment", "label": "Есть инвестиции"},
                ],
                "is_required": True,
                "is_filterable": True,
            },
            _WORKLOAD_FIELD,
            _TECH_FORMAT_FIELD,
        ],
    ),
    *_with_defaults(
        "product_project",
        [
            {
                "key": "specialization",
                "label": "Специализация",
                "field_type": RoleFieldType.SELECT,
                "options": [
                    {"value": "product_manager", "label": "Product Manager"},
                    {"value": "project_manager", "label": "Project Manager"},
                    {"value": "scrum_master", "label": "Scrum Master"},
                ],
                "is_required": True,
                "is_filterable": True,
            },
            {"key": "grade", "label": "Грейд", "field_type": RoleFieldType.SELECT, "options": _GRADE_OPTIONS,
             "is_required": True, "is_filterable": True},
            _WORKLOAD_FIELD,
            _TECH_FORMAT_FIELD,
        ],
    ),
    *_with_defaults(
        "engineering",
        [
            {
                "key": "specialization",
                "label": "Направление",
                "field_type": RoleFieldType.SELECT,
                "options": [
                    {"value": "backend", "label": "Backend"},
                    {"value": "frontend", "label": "Frontend"},
                    {"value": "fullstack", "label": "Fullstack"},
                    {"value": "mobile", "label": "Mobile"},
                    {"value": "devops", "label": "DevOps"},
                    {"value": "qa", "label": "QA"},
                    {"value": "data_ai_ml", "label": "Data Science/AI/ML"},
                ],
                "is_required": True,
                "is_filterable": True,
            },
            {"key": "grade", "label": "Грейд", "field_type": RoleFieldType.SELECT, "options": _GRADE_OPTIONS,
             "is_required": True, "is_filterable": True},
            _WORKLOAD_FIELD,
            _TECH_FORMAT_FIELD,
        ],
    ),
    *_with_defaults(
        "design",
        [
            {
                "key": "specialization",
                "label": "Направление",
                "field_type": RoleFieldType.SELECT,
                "options": [
                    {"value": "ui_ux_web", "label": "UI/UX & Web"},
                    {"value": "brand_graphic", "label": "Brand & Graphic"},
                    {"value": "motion_3d", "label": "3D/Motion"},
                ],
                "is_required": True,
                "is_filterable": True,
            },
            {"key": "grade", "label": "Грейд", "field_type": RoleFieldType.SELECT, "options": _GRADE_OPTIONS,
             "is_required": True, "is_filterable": True},
            _WORKLOAD_FIELD,
            _TECH_FORMAT_FIELD,
        ],
    ),
    *_with_defaults(
        "marketing",
        [
            {
                "key": "specialization",
                "label": "Специализация",
                "field_type": RoleFieldType.SELECT,
                "options": [
                    {"value": "performance", "label": "Performance"},
                    {"value": "content_smm", "label": "Content & SMM"},
                    {"value": "seo_pr", "label": "SEO & PR"},
                    {"value": "growth_hacking", "label": "Growth Hacking"},
                ],
                "is_required": True,
                "is_filterable": True,
            },
            _WORKLOAD_FIELD,
            _TECH_FORMAT_FIELD,
        ],
    ),
    *_with_defaults(
        "sales_bizdev",
        [
            {
                "key": "specialization",
                "label": "Специализация",
                "field_type": RoleFieldType.SELECT,
                "options": [
                    {"value": "b2b_sales", "label": "B2B Sales"},
                    {"value": "partnerships", "label": "Partnerships"},
                ],
                "is_required": True,
                "is_filterable": True,
            },
            _WORKLOAD_FIELD,
            _TECH_FORMAT_FIELD,
        ],
    ),
    *_with_defaults(
        "finance_legal",
        [
            {
                "key": "specialization",
                "label": "Специализация",
                "field_type": RoleFieldType.SELECT,
                "options": [
                    {"value": "investor", "label": "Инвестор"},
                    {"value": "financial_analyst", "label": "Фин. аналитик"},
                    {"value": "lawyer", "label": "Юрист"},
                ],
                "is_required": True,
                "is_filterable": True,
            },
            _WORKLOAD_FIELD,
            _TECH_FORMAT_FIELD,
        ],
    ),
    *_with_defaults(
        "study_mate",
        [
            {
                "key": "goal",
                "label": "Цель",
                "field_type": RoleFieldType.SELECT,
                "options": [
                    {"value": "exams", "label": "Экзамены"},
                    {"value": "admission", "label": "Поступление"},
                    {"value": "topic_study", "label": "Изучение темы"},
                ],
                "is_required": True,
                "is_filterable": True,
            },
            {
                "key": "level",
                "label": "Уровень",
                "field_type": RoleFieldType.SELECT,
                "options": [
                    {"value": "beginner", "label": "Новичок"},
                    {"value": "basic", "label": "Базовый"},
                    {"value": "advanced", "label": "Продвинутый"},
                ],
                "is_required": True,
                "is_filterable": True,
            },
            _EDU_FREQUENCY_FIELD,
            _EDU_FORMAT_FIELD,
        ],
    ),
    *_with_defaults(
        "language_buddy",
        [
            {
                "key": "level",
                "label": "Уровень языка",
                "field_type": RoleFieldType.SELECT,
                "options": [{"value": v, "label": v.upper()} for v in ["a1", "a2", "b1", "b2", "c1", "c2"]],
                "is_required": True,
                "is_filterable": True,
            },
            {
                "key": "format",
                "label": "Формат",
                "field_type": RoleFieldType.SELECT,
                "options": [
                    {"value": "calls", "label": "Созвоны"},
                    {"value": "chat", "label": "Переписка"},
                    {"value": "in_person", "label": "Очные встречи"},
                ],
                "is_required": True,
                "is_filterable": True,
            },
            _EDU_FREQUENCY_FIELD,
        ],
    ),
    *_with_defaults(
        "pet_project_partner",
        [
            {
                "key": "goal",
                "label": "Цель",
                "field_type": RoleFieldType.SELECT,
                "options": [
                    {"value": "hackathon", "label": "Хакатон"},
                    {"value": "growth", "label": "Развитие"},
                    {"value": "portfolio", "label": "Портфолио"},
                ],
                "is_required": True,
                "is_filterable": True,
            },
            _EDU_FREQUENCY_FIELD,
            _EDU_FORMAT_FIELD,
        ],
    ),
    *_with_defaults(
        "mentor_mentee",
        [
            {
                "key": "looking_for",
                "label": "Кого ищу",
                "field_type": RoleFieldType.SELECT,
                "options": [
                    {"value": "mentor", "label": "Ментора"},
                    {"value": "mentee", "label": "Готов менторить"},
                ],
                "is_required": True,
                "is_filterable": True,
            },
            _EDU_FREQUENCY_FIELD,
            _EDU_FORMAT_FIELD,
        ],
    ),
]

TAGS_BY_ROLE = {
    "founder": ["B2B", "AI", "SaaS", "No-code", "B2C", "Fintech", "Marketplace", "EdTech", "Bootstrapping"],
    "product_project": [
        "Agile",
        "Scrum",
        "Unit Economics",
        "Roadmap",
        "Discovery",
        "A/B Testing",
        "Product Analytics",
        "Jira",
    ],
    "engineering": [
        "Python",
        "React",
        "PostgreSQL",
        "Docker",
        "TypeScript",
        "FastAPI",
        "Node.js",
        "Kubernetes",
        "Go",
        "CI/CD",
    ],
    "design": [
        "Figma",
        "Web Design",
        "3D",
        "Motion",
        "UI/UX",
        "Branding",
        "Design Systems",
        "Illustration",
    ],
    "marketing": ["Performance", "SMM", "SEO", "PR", "Content", "Email Marketing", "Analytics", "Growth"],
    "sales_bizdev": [
        "B2B Sales",
        "Partnerships",
        "Outreach",
        "Cold Calling",
        "CRM",
        "Negotiation",
        "Lead Generation",
        "Account Management",
    ],
    "finance_legal": [
        "Investor",
        "Financial Model",
        "Law",
        "Fundraising",
        "Accounting",
        "Tax",
        "Contracts",
        "IP",
    ],
    "study_mate": [
        "Higher Math",
        "Exams",
        "Data Science",
        "Physics",
        "Algorithms",
        "Statistics",
        "Research",
        "Study Group",
    ],
    "language_buddy": [
        "English",
        "Speaking Club",
        "IELTS",
        "German",
        "Spanish",
        "French",
        "Business English",
        "TOEFL",
    ],
    "pet_project_partner": [
        "Hackathon",
        "Portfolio Building",
        "Open Source",
        "Side Project",
        "Game Dev",
        "Mobile",
        "Web3",
        "Machine Learning",
    ],
    "mentor_mentee": [
        "Career Growth",
        "Mock Interview",
        "Code Review",
        "Resume",
        "Leadership",
        "Soft Skills",
        "Interview Prep",
        "Career Change",
    ],
}


async def _seed_categories(session: AsyncSession) -> dict[str, int]:
    stmt = pg_insert(CategoryModel).values(CATEGORIES).on_conflict_do_nothing(index_elements=["slug"])
    await session.execute(stmt)
    result = await session.execute(select(CategoryModel.id, CategoryModel.slug))
    return {slug: id_ for id_, slug in result.all()}


async def _seed_roles(session: AsyncSession, category_ids: dict[str, int]) -> dict[str, int]:
    values = [
        {
            "category_id": category_ids[r["category_slug"]],
            "slug": r["slug"],
            "title": r["title"],
            "sort_order": r["sort_order"],
        }
        for r in ROLES
    ]
    stmt = pg_insert(RoleModel).values(values).on_conflict_do_nothing(
        index_elements=["category_id", "slug"]
    )
    await session.execute(stmt)
    result = await session.execute(select(RoleModel.id, RoleModel.slug))
    return {slug: id_ for id_, slug in result.all()}


async def _seed_role_fields(session: AsyncSession, role_ids: dict[str, int]) -> None:
    values = [
        {
            "role_id": role_ids[f["role_slug"]],
            "key": f["key"],
            "label": f["label"],
            "field_type": f["field_type"],
            "options": f["options"],
            "is_required": f["is_required"],
            "is_filterable": f["is_filterable"],
            "sort_order": f["sort_order"],
        }
        for f in ROLE_FIELDS
    ]
    stmt = pg_insert(RoleFieldModel).values(values).on_conflict_do_nothing(
        index_elements=["role_id", "key"]
    )
    await session.execute(stmt)


async def _seed_tags(session: AsyncSession, role_ids: dict[str, int], category_ids: dict[str, int]) -> None:
    all_titles = {normalize_tag_title(title): title for titles in TAGS_BY_ROLE.values() for title in titles}
    tag_values = [
        {
            "title": title,
            "normalized_title": normalized_title,
            "status": TagStatus.APPROVED,
            "created_by_user_id": None,
            "usage_count": 0,
        }
        for normalized_title, title in all_titles.items()
    ]
    stmt = pg_insert(TagModel).values(tag_values).on_conflict_do_nothing(index_elements=["normalized_title"])
    await session.execute(stmt)

    result = await session.execute(select(TagModel.id, TagModel.normalized_title))
    tag_ids = {normalized_title: id_ for id_, normalized_title in result.all()}

    role_to_category_slug = {r["slug"]: r["category_slug"] for r in ROLES}
    scope_values = [
        {
            "tag_id": tag_ids[normalize_tag_title(title)],
            "category_id": category_ids[role_to_category_slug[role_slug]],
            "role_id": role_ids[role_slug],
        }
        for role_slug, titles in TAGS_BY_ROLE.items()
        for title in titles
    ]
    stmt = pg_insert(TagScopeModel).values(scope_values).on_conflict_do_nothing(
        index_elements=["tag_id", "category_id", "role_id"]
    )
    await session.execute(stmt)


async def _invalidate_taxonomy_cache() -> None:
    # Own client: the module-level redis_helper.client is bound to the event loop it was created in.
    client = Redis.from_url(
        str(settings.redis.url),
        decode_responses=True,
        socket_connect_timeout=settings.redis.socket_timeout,
        socket_timeout=settings.redis.socket_timeout,
    )
    try:
        keys = [key async for key in client.scan_iter(match="taxonomy:*")]
        if keys:
            await client.delete(*keys)
    except RedisError:
        logger.warning("Could not clear the taxonomy cache; stale values live until their TTL", exc_info=True)
    finally:
        await client.aclose()


async def main() -> None:
    async with db_helper.session_factory() as session:
        category_ids = await _seed_categories(session)
        role_ids = await _seed_roles(session, category_ids)
        await _seed_role_fields(session, role_ids)
        await _seed_tags(session, role_ids, category_ids)
        await session.commit()
    await _invalidate_taxonomy_cache()
    print("Taxonomy seed done.")


if __name__ == "__main__":
    asyncio.run(main())
