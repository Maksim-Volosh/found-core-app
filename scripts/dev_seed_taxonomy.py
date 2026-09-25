"""Dev-only: наполняет таблицы categories/roles/role_fields/tags/tag_scopes
базовыми данными из ТЗ (раздел 3) и схемы ролей. Идемпотентно — повторный
запуск ничего не задваивает (ON CONFLICT DO NOTHING по уникальным полям).

Использование:
    python -m scripts.dev_seed_taxonomy
"""

import asyncio

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import RoleFieldType, TagStatus
from app.infrastructure.helpers import db_helper
from app.infrastructure.models import CategoryModel, RoleFieldModel, RoleModel, TagModel, TagScopeModel

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
    "founder": [("b2b", "B2B"), ("ai", "AI"), ("saas", "SaaS"), ("no_code", "No-code")],
    "product_project": [("agile", "Agile"), ("scrum", "Scrum"), ("unit_economics", "Unit Economics")],
    "engineering": [("python", "Python"), ("react", "React"), ("postgres", "PostgreSQL"), ("docker", "Docker")],
    "design": [("figma", "Figma"), ("web_design", "Web Design"), ("3d", "3D"), ("motion", "Motion")],
    "marketing": [("performance", "Performance"), ("smm", "SMM"), ("seo", "SEO"), ("pr", "PR")],
    "sales_bizdev": [
        ("b2b_sales", "B2B Sales"),
        ("partnerships", "Partnerships"),
        ("outreach", "Outreach"),
    ],
    "finance_legal": [
        ("investor", "Investor"),
        ("financial_model", "Financial Model"),
        ("law", "Law"),
    ],
    "study_mate": [
        ("higher_math", "Higher Math"),
        ("exams", "Exams"),
        ("data_science", "Data Science"),
    ],
    "language_buddy": [("english", "English"), ("speaking_club", "Speaking Club"), ("ielts", "IELTS")],
    "pet_project_partner": [("hackathon", "Hackathon"), ("portfolio_building", "Portfolio Building")],
    "mentor_mentee": [("career_growth", "Career Growth"), ("mock_interview", "Mock Interview")],
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
    all_tags = {slug: title for tags in TAGS_BY_ROLE.values() for slug, title in tags}
    tag_values = [
        {"slug": slug, "title": title, "status": TagStatus.APPROVED, "created_by_user_id": None, "usage_count": 0}
        for slug, title in all_tags.items()
    ]
    stmt = pg_insert(TagModel).values(tag_values).on_conflict_do_nothing(index_elements=["slug"])
    await session.execute(stmt)

    result = await session.execute(select(TagModel.id, TagModel.slug))
    tag_ids = {slug: id_ for id_, slug in result.all()}

    role_to_category_slug = {r["slug"]: r["category_slug"] for r in ROLES}
    scope_values = [
        {
            "tag_id": tag_ids[slug],
            "category_id": category_ids[role_to_category_slug[role_slug]],
            "role_id": role_ids[role_slug],
        }
        for role_slug, tags in TAGS_BY_ROLE.items()
        for slug, _ in tags
    ]
    stmt = pg_insert(TagScopeModel).values(scope_values).on_conflict_do_nothing(
        index_elements=["tag_id", "category_id", "role_id"]
    )
    await session.execute(stmt)


async def main() -> None:
    async with db_helper.session_factory() as session:
        category_ids = await _seed_categories(session)
        role_ids = await _seed_roles(session, category_ids)
        await _seed_role_fields(session, role_ids)
        await _seed_tags(session, role_ids, category_ids)
        await session.commit()
    print("Taxonomy seed done.")


if __name__ == "__main__":
    asyncio.run(main())
