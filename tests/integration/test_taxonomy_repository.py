import asyncio

from app.core.config import settings
from app.domain.entities import NewTagEntity, NewTagScopeEntity
from app.domain.enums import RoleFieldType, TagStatus
from app.infrastructure.helpers import db_helper
from app.infrastructure.models import RoleModel
from app.infrastructure.repositories.sqlalchemy_taxonomy import SqlAlchemyTaxonomyRepository
from tests.fixtures.auth import create_user_with_headers
from tests.fixtures.taxonomy_data import add_tag, count_tag_scopes, count_tags


def _repo(session, suggest_limit: int | None = None) -> SqlAlchemyTaxonomyRepository:
    return SqlAlchemyTaxonomyRepository(
        session, suggest_limit=suggest_limit or settings.taxonomy.suggest_limit
    )


def _new_tag(title: str = "Node.js", normalized_title: str = "node.js", user_id: int | None = None):
    return NewTagEntity(
        title=title,
        normalized_title=normalized_title,
        status=TagStatus.PENDING,
        created_by_user_id=user_id,
    )


class TestReferenceData:
    async def test_get_categories_ordered_by_sort_order(self, session, taxonomy_data):
        categories = await _repo(session).get_categories()

        assert [c.slug for c in categories] == ["tech_product", "edu_growth"]

    async def test_equal_sort_order_falls_back_to_id(self, session, taxonomy_data):
        t = taxonomy_data
        for slug in ("zeta", "alpha", "mid"):
            session.add(RoleModel(category_id=t.edu_category_id, slug=slug, title=slug, sort_order=9))
        await session.commit()

        roles = await _repo(session).get_roles_by_category(t.edu_category_id)

        tied = [r for r in roles if r.sort_order == 9]
        assert [r.slug for r in tied] == ["zeta", "alpha", "mid"]  # insertion (id) order, not alphabetical
        assert [r.id for r in tied] == sorted(r.id for r in tied)

    async def test_get_category_by_id_found_and_missing(self, session, taxonomy_data):
        repo = _repo(session)

        found = await repo.get_category_by_id(taxonomy_data.tech_category_id)
        missing = await repo.get_category_by_id(999999)

        assert found is not None and found.slug == "tech_product"
        assert missing is None

    async def test_get_roles_by_category_only_returns_that_category(self, session, taxonomy_data):
        roles = await _repo(session).get_roles_by_category(taxonomy_data.tech_category_id)

        assert [r.slug for r in roles] == ["engineering", "design"]

    async def test_get_role_by_id_found_and_missing(self, session, taxonomy_data):
        repo = _repo(session)

        found = await repo.get_role_by_id(taxonomy_data.study_mate_role_id)
        missing = await repo.get_role_by_id(999999)

        assert found is not None and found.category_id == taxonomy_data.edu_category_id
        assert missing is None

    async def test_get_role_fields_maps_enum_and_options(self, session, taxonomy_data):
        fields = await _repo(session).get_role_fields_by_role(taxonomy_data.engineering_role_id)

        assert len(fields) == 1
        assert fields[0].key == "grade"
        assert fields[0].field_type is RoleFieldType.SELECT
        assert fields[0].options == [
            {"value": "junior", "label": "Junior"},
            {"value": "middle", "label": "Middle"},
        ]

    async def test_get_role_fields_for_role_without_fields_is_empty(self, session, taxonomy_data):
        assert await _repo(session).get_role_fields_by_role(taxonomy_data.design_role_id) == []


class TestCreateTag:
    async def test_new_tag_is_returned_as_entity(self, session):
        tag = await _repo(session).create_tag(_new_tag())

        assert tag is not None
        assert tag.id is not None
        assert tag.title == "Node.js"
        assert tag.status is TagStatus.PENDING
        assert tag.usage_count == 0

    async def test_duplicate_normalized_title_returns_none_without_raising(self, session):
        repo = _repo(session)
        await repo.create_tag(_new_tag())

        second = await repo.create_tag(_new_tag(title="NODE.JS"))

        assert second is None
        assert await count_tags(session) == 1

    async def test_session_is_still_usable_after_a_conflict(self, session):
        repo = _repo(session)
        first = await repo.create_tag(_new_tag())
        await repo.create_tag(_new_tag(title="NODE.JS"))

        found = await repo.get_tag_by_normalized_title("node.js")

        assert found is not None
        assert found.id == first.id
        assert found.title == "Node.js"  # the first writer's title stays canonical

    async def test_get_tag_by_normalized_title_missing(self, session):
        assert await _repo(session).get_tag_by_normalized_title("nope") is None

    async def test_concurrent_inserts_of_the_same_title_produce_one_row(self, session):
        async def insert():
            async with db_helper.session_factory() as s:
                tag = await _repo(s).create_tag(_new_tag())
                # Releases the row lock so the competing inserts can resolve their conflict.
                await s.commit()
                return tag

        results = await asyncio.gather(insert(), insert(), insert())

        assert sum(r is not None for r in results) == 1
        assert sum(r is None for r in results) == 2
        assert await count_tags(session) == 1

    async def test_created_by_user_id_is_stored(self, session):
        user, _ = await create_user_with_headers(session, telegram_id=910001)

        tag = await _repo(session).create_tag(_new_tag(user_id=user.id))

        assert tag.created_by_user_id == user.id


class TestCreateTagScope:
    async def test_scope_insert_is_idempotent(self, session, taxonomy_data):
        repo = _repo(session)
        tag = await repo.create_tag(_new_tag())
        scope = NewTagScopeEntity(
            tag_id=tag.id,
            category_id=taxonomy_data.tech_category_id,
            role_id=taxonomy_data.engineering_role_id,
        )

        await repo.create_tag_scope(scope)
        await repo.create_tag_scope(scope)

        assert await count_tag_scopes(session) == 1

    async def test_category_wide_scope_with_null_role_is_idempotent(self, session, taxonomy_data):
        # NULLS NOT DISTINCT: two (tag, category, NULL) rows must collapse into one.
        repo = _repo(session)
        tag = await repo.create_tag(_new_tag())
        scope = NewTagScopeEntity(tag_id=tag.id, category_id=taxonomy_data.tech_category_id, role_id=None)

        await repo.create_tag_scope(scope)
        await repo.create_tag_scope(scope)

        assert await count_tag_scopes(session) == 1

    async def test_different_scopes_for_the_same_tag_coexist(self, session, taxonomy_data):
        repo = _repo(session)
        tag = await repo.create_tag(_new_tag())

        await repo.create_tag_scope(
            NewTagScopeEntity(tag.id, taxonomy_data.tech_category_id, taxonomy_data.engineering_role_id)
        )
        await repo.create_tag_scope(NewTagScopeEntity(tag.id, taxonomy_data.tech_category_id, None))
        await repo.create_tag_scope(
            NewTagScopeEntity(tag.id, taxonomy_data.edu_category_id, taxonomy_data.study_mate_role_id)
        )

        assert await count_tag_scopes(session) == 3


class TestSuggestTags:
    async def test_role_specific_scope_matches_only_that_role(self, session, taxonomy_data):
        t = taxonomy_data
        await add_tag(session, "Python", scopes=[(t.tech_category_id, t.engineering_role_id)])
        repo = _repo(session)

        in_role = await repo.suggest_tags("py", t.tech_category_id, t.engineering_role_id, user_id=0)
        other_role = await repo.suggest_tags("py", t.tech_category_id, t.design_role_id, user_id=0)
        category_only = await repo.suggest_tags("py", t.tech_category_id, None, user_id=0)

        assert [x.title for x in in_role] == ["Python"]
        assert other_role == []
        assert category_only == []

    async def test_category_wide_scope_matches_every_role_in_the_category(self, session, taxonomy_data):
        t = taxonomy_data
        await add_tag(session, "Teamwork", scopes=[(t.tech_category_id, None)])
        repo = _repo(session)

        for role_id in (t.engineering_role_id, t.design_role_id, None):
            found = await repo.suggest_tags("team", t.tech_category_id, role_id, user_id=0)
            assert [x.title for x in found] == ["Teamwork"]

    async def test_scope_in_another_category_is_not_returned(self, session, taxonomy_data):
        t = taxonomy_data
        await add_tag(session, "Anki", scopes=[(t.edu_category_id, t.study_mate_role_id)])

        found = await _repo(session).suggest_tags("anki", t.tech_category_id, None, user_id=0)

        assert found == []

    async def test_match_is_case_insensitive_substring(self, session, taxonomy_data):
        t = taxonomy_data
        await add_tag(session, "Python", scopes=[(t.tech_category_id, None)])
        repo = _repo(session)

        for query in ("yth", "PYTH", "Python"):
            found = await repo.suggest_tags(query, t.tech_category_id, None, user_id=0)
            assert [x.title for x in found] == ["Python"]

    async def test_like_wildcards_in_the_query_match_literally(self, session, taxonomy_data):
        t = taxonomy_data
        scope = [(t.tech_category_id, None)]
        for title in ("C#", "C++", "CI/CD", "snake_case", "100%"):
            await add_tag(session, title, scopes=scope)
        repo = _repo(session)

        async def titles(query: str) -> list[str]:
            found = await repo.suggest_tags(query, t.tech_category_id, None, user_id=0)
            return sorted(x.title for x in found)

        assert await titles("%") == ["100%"]  # not "everything"
        assert await titles("_") == ["snake_case"]  # not "any single character"
        assert await titles("C_") == []  # not "C followed by any character"
        assert await titles("e_c") == ["snake_case"]

    async def test_backslash_in_the_query_is_a_plain_character(self, session, taxonomy_data):
        t = taxonomy_data
        await add_tag(session, "Python", scopes=[(t.tech_category_id, None)])

        found = await _repo(session).suggest_tags("\\", t.tech_category_id, None, user_id=0)

        assert found == []

    async def test_pending_tags_are_visible_only_to_their_author(self, session, taxonomy_data):
        t = taxonomy_data
        author, _ = await create_user_with_headers(session, telegram_id=910002)
        other, _ = await create_user_with_headers(session, telegram_id=910003)
        await add_tag(
            session,
            "Zig",
            status=TagStatus.PENDING,
            created_by=author.id,
            scopes=[(t.tech_category_id, None)],
        )
        repo = _repo(session)

        for_author = await repo.suggest_tags("zig", t.tech_category_id, None, user_id=author.id)
        for_other = await repo.suggest_tags("zig", t.tech_category_id, None, user_id=other.id)

        assert [x.title for x in for_author] == ["Zig"]
        assert for_other == []

    async def test_rejected_tags_are_hidden_even_from_their_author(self, session, taxonomy_data):
        t = taxonomy_data
        author, _ = await create_user_with_headers(session, telegram_id=910004)
        await add_tag(
            session,
            "Spam",
            status=TagStatus.REJECTED,
            created_by=author.id,
            scopes=[(t.tech_category_id, None)],
        )

        found = await _repo(session).suggest_tags("spam", t.tech_category_id, None, user_id=author.id)

        assert found == []

    async def test_ordered_by_usage_count_desc(self, session, taxonomy_data):
        t = taxonomy_data
        scope = [(t.tech_category_id, None)]
        await add_tag(session, "Tool Low", usage_count=1, scopes=scope)
        await add_tag(session, "Tool High", usage_count=50, scopes=scope)
        await add_tag(session, "Tool Mid", usage_count=10, scopes=scope)

        found = await _repo(session).suggest_tags("tool", t.tech_category_id, None, user_id=0)

        assert [x.title for x in found] == ["Tool High", "Tool Mid", "Tool Low"]

    async def test_equal_usage_count_is_ordered_by_title_then_id(self, session, taxonomy_data):
        t = taxonomy_data
        scope = [(t.tech_category_id, None)]
        for title in ("Tool C", "Tool A", "Tool B"):  # inserted out of alphabetical order on purpose
            await add_tag(session, title, usage_count=5, scopes=scope)
        repo = _repo(session)

        first = await repo.suggest_tags("tool", t.tech_category_id, None, user_id=0)
        second = await repo.suggest_tags("tool", t.tech_category_id, None, user_id=0)

        assert [x.title for x in first] == ["Tool A", "Tool B", "Tool C"]
        assert [x.id for x in second] == [x.id for x in first]

    async def test_cyrillic_query_matches_regardless_of_case(self, session, taxonomy_data):
        t = taxonomy_data
        await add_tag(session, "Питон", scopes=[(t.tech_category_id, None)])
        repo = _repo(session)

        for query in ("питон", "ПИТОН", "Пит", "итон"):
            found = await repo.suggest_tags(query, t.tech_category_id, None, user_id=0)
            assert [x.title for x in found] == ["Питон"], query

    async def test_tag_with_several_matching_scopes_is_returned_once(self, session, taxonomy_data):
        t = taxonomy_data
        await add_tag(
            session,
            "Figma",
            scopes=[
                (t.tech_category_id, t.engineering_role_id),
                (t.tech_category_id, t.design_role_id),
                (t.tech_category_id, None),
            ],
        )

        found = await _repo(session).suggest_tags("figma", t.tech_category_id, t.design_role_id, user_id=0)

        assert [x.title for x in found] == ["Figma"]

    async def test_limit_is_respected(self, session, taxonomy_data):
        t = taxonomy_data
        for i in range(5):
            await add_tag(session, f"Lib {i}", usage_count=i, scopes=[(t.tech_category_id, None)])

        found = await _repo(session, suggest_limit=2).suggest_tags("lib", t.tech_category_id, None, user_id=0)

        assert len(found) == 2
