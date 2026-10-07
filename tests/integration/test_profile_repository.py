import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app.domain.enums import ProfileStatus
from app.infrastructure.helpers import db_helper
from app.infrastructure.repositories import SqlAlchemyProfileRepository, SqlAlchemyUserRepository
from tests.fixtures.auth import create_user_with_headers
from tests.fixtures.factories import make_new_profile_entity
from tests.fixtures.taxonomy_data import add_tag


async def _create_tags(session, taxonomy_data, count: int) -> list[int]:
    """Approved tags scoped to the engineering role; returns their ids."""
    t = taxonomy_data
    tags = [
        await add_tag(session, f"tag-{i}", scopes=[(t.tech_category_id, t.engineering_role_id)])
        for i in range(count)
    ]
    return [tag.id for tag in tags]


def _new_profile(taxonomy_data, user_id: int, tag_ids: list[int], **overrides):
    defaults = dict(
        user_id=user_id,
        category_id=taxonomy_data.tech_category_id,
        role_id=taxonomy_data.engineering_role_id,
        tag_ids=tag_ids,
    )
    defaults.update(overrides)
    return make_new_profile_entity(**defaults)


async def test_create_returns_profile_with_tags_ordered_by_tag_id(session, taxonomy_data):
    user, _ = await create_user_with_headers(session, telegram_id=1)
    tag_ids = await _create_tags(session, taxonomy_data, 5)

    created = await SqlAlchemyProfileRepository(session).create(
        _new_profile(taxonomy_data, user.id, list(reversed(tag_ids)))
    )

    assert created is not None
    assert [t.id for t in created.tags] == sorted(tag_ids)
    assert created.status is ProfileStatus.ACTIVE


async def test_create_returns_none_for_the_same_user_category_and_role(session, taxonomy_data):
    user, _ = await create_user_with_headers(session, telegram_id=1)
    tag_ids = await _create_tags(session, taxonomy_data, 5)
    repo = SqlAlchemyProfileRepository(session)
    await repo.create(_new_profile(taxonomy_data, user.id, tag_ids))

    second = await repo.create(_new_profile(taxonomy_data, user.id, tag_ids))

    assert second is None
    assert (await session.execute(text("SELECT count(*) FROM profiles"))).scalar_one() == 1


async def test_concurrent_creates_of_the_same_role_produce_one_row(session, taxonomy_data):
    user, _ = await create_user_with_headers(session, telegram_id=1)
    tag_ids = await _create_tags(session, taxonomy_data, 5)

    async def insert():
        async with db_helper.session_factory() as s:
            profile = await SqlAlchemyProfileRepository(s).create(
                _new_profile(taxonomy_data, user.id, tag_ids)
            )
            await s.commit()
            return profile

    results = await asyncio.gather(*[insert() for _ in range(5)])

    assert sum(r is not None for r in results) == 1
    assert (await session.execute(text("SELECT count(*) FROM profiles"))).scalar_one() == 1
    assert (await session.execute(text("SELECT count(*) FROM profile_tags"))).scalar_one() == 5


async def test_list_by_user_id_is_ordered_by_created_at_then_id(session, taxonomy_data):
    t = taxonomy_data
    user, _ = await create_user_with_headers(session, telegram_id=1)
    tag_ids = await _create_tags(session, taxonomy_data, 5)
    repo = SqlAlchemyProfileRepository(session)
    now = datetime.now(timezone.utc)
    newest = await repo.create(_new_profile(t, user.id, tag_ids, created_at=now))
    oldest = await repo.create(
        _new_profile(t, user.id, tag_ids, role_id=t.design_role_id, created_at=now - timedelta(days=1))
    )

    profiles = await repo.list_by_user_id(user.id)

    assert [p.id for p in profiles] == [oldest.id, newest.id]


async def test_list_by_user_id_returns_only_own_profiles_with_their_tags(session, taxonomy_data):
    tag_ids = await _create_tags(session, taxonomy_data, 6)
    first_user, _ = await create_user_with_headers(session, telegram_id=1)
    second_user, _ = await create_user_with_headers(session, telegram_id=2)
    repo = SqlAlchemyProfileRepository(session)
    await repo.create(_new_profile(taxonomy_data, first_user.id, tag_ids[:5]))
    await repo.create(_new_profile(taxonomy_data, second_user.id, tag_ids[1:]))

    profiles = await repo.list_by_user_id(first_user.id)

    assert len(profiles) == 1
    assert [t.id for t in profiles[0].tags] == tag_ids[:5]


async def test_get_newest_active_skips_paused_and_picks_latest(session, taxonomy_data):
    t = taxonomy_data
    user, _ = await create_user_with_headers(session, telegram_id=1)
    tag_ids = await _create_tags(session, taxonomy_data, 5)
    repo = SqlAlchemyProfileRepository(session)
    now = datetime.now(timezone.utc)
    older = await repo.create(_new_profile(t, user.id, tag_ids, created_at=now - timedelta(days=2)))
    await repo.create(
        _new_profile(
            t,
            user.id,
            tag_ids,
            role_id=t.design_role_id,
            created_at=now,
            status=ProfileStatus.PAUSED,
        )
    )

    newest_active = await repo.get_newest_active_by_user_id(user.id)

    assert newest_active.id == older.id


async def test_update_replaces_content_and_tags_but_not_status(session, taxonomy_data):
    user, _ = await create_user_with_headers(session, telegram_id=1)
    tag_ids = await _create_tags(session, taxonomy_data, 8)
    repo = SqlAlchemyProfileRepository(session)
    created = await repo.create(
        _new_profile(taxonomy_data, user.id, tag_ids[:5], status=ProfileStatus.PAUSED)
    )

    created.bio = "new bio"
    created.extra_attributes = {"grade": "senior"}
    created.status = ProfileStatus.ACTIVE
    updated = await repo.update(created, tag_ids[3:])

    assert updated.bio == "new bio"
    assert updated.extra_attributes == {"grade": "senior"}
    assert [t.id for t in updated.tags] == tag_ids[3:]
    assert updated.status is ProfileStatus.PAUSED


async def test_concurrent_updates_do_not_collide_on_profile_tags(session, taxonomy_data):
    user, _ = await create_user_with_headers(session, telegram_id=1)
    tag_ids = await _create_tags(session, taxonomy_data, 5)
    created = await SqlAlchemyProfileRepository(session).create(_new_profile(taxonomy_data, user.id, tag_ids))
    await session.commit()

    async def put():
        async with db_helper.session_factory() as s:
            repo = SqlAlchemyProfileRepository(s)
            profile = await repo.get_by_id(created.id)
            await repo.update(profile, tag_ids)
            await s.commit()

    await asyncio.gather(*[put() for _ in range(5)])

    assert (await session.execute(text("SELECT count(*) FROM profile_tags"))).scalar_one() == 5


async def test_set_status_changes_only_status(session, taxonomy_data):
    user, _ = await create_user_with_headers(session, telegram_id=1)
    tag_ids = await _create_tags(session, taxonomy_data, 5)
    repo = SqlAlchemyProfileRepository(session)
    created = await repo.create(_new_profile(taxonomy_data, user.id, tag_ids))

    await repo.set_status(created.id, ProfileStatus.PAUSED)

    session.expire_all()
    paused = await repo.get_by_id(created.id)
    assert paused.status is ProfileStatus.PAUSED
    assert paused.bio == created.bio


async def test_delete_removes_links_but_keeps_tags(session, taxonomy_data):
    user, _ = await create_user_with_headers(session, telegram_id=1)
    tag_ids = await _create_tags(session, taxonomy_data, 5)
    repo = SqlAlchemyProfileRepository(session)
    created = await repo.create(_new_profile(taxonomy_data, user.id, tag_ids))

    await repo.delete(created.id)
    await session.commit()

    assert await repo.get_by_id(created.id) is None
    assert (await session.execute(text("SELECT count(*) FROM profile_tags"))).scalar_one() == 0
    assert (await session.execute(text("SELECT count(*) FROM tags"))).scalar_one() == 5


async def test_deleting_a_tag_removes_it_from_profiles(session, taxonomy_data):
    user, _ = await create_user_with_headers(session, telegram_id=1)
    tag_ids = await _create_tags(session, taxonomy_data, 5)
    repo = SqlAlchemyProfileRepository(session)
    created = await repo.create(_new_profile(taxonomy_data, user.id, tag_ids))

    await session.execute(text("DELETE FROM tags WHERE id = :id"), {"id": tag_ids[0]})
    await session.commit()

    profile = await repo.get_by_id(created.id)
    assert [t.id for t in profile.tags] == tag_ids[1:]


async def test_deleting_the_active_profile_nulls_users_active_profile_id(session, taxonomy_data):
    user, _ = await create_user_with_headers(session, telegram_id=1)
    tag_ids = await _create_tags(session, taxonomy_data, 5)
    profile_repo = SqlAlchemyProfileRepository(session)
    created = await profile_repo.create(_new_profile(taxonomy_data, user.id, tag_ids))
    await SqlAlchemyUserRepository(session).set_active_profile(user.id, created.id)
    await session.commit()

    await profile_repo.delete(created.id)
    await session.commit()

    active = (
        await session.execute(text("SELECT active_profile_id FROM users WHERE id = :id"), {"id": user.id})
    ).scalar_one()
    assert active is None


async def test_set_active_profile_persists_and_clears(session, taxonomy_data):
    user, _ = await create_user_with_headers(session, telegram_id=1)
    tag_ids = await _create_tags(session, taxonomy_data, 5)
    created = await SqlAlchemyProfileRepository(session).create(_new_profile(taxonomy_data, user.id, tag_ids))
    user_repo = SqlAlchemyUserRepository(session)

    await user_repo.set_active_profile(user.id, created.id)
    session.expire_all()
    assert (await user_repo.get_by_id(user.id)).active_profile_id == created.id

    await user_repo.set_active_profile(user.id, None)
    session.expire_all()
    assert (await user_repo.get_by_id(user.id)).active_profile_id is None
