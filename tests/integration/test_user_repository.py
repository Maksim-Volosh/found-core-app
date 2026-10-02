import asyncio

from sqlalchemy import text

from app.infrastructure.helpers import db_helper
from app.infrastructure.repositories.user import SqlAlchemyUserRepository
from tests.fixtures.factories import make_new_user_entity


async def test_create_persists_and_assigns_defaults(session):
    repo = SqlAlchemyUserRepository(session)

    entity = await repo.create(make_new_user_entity(telegram_id=111))

    assert entity is not None
    assert entity.id is not None
    assert entity.is_admin is False
    assert entity.is_banned is False
    assert entity.token_version == 0


async def test_get_by_telegram_id_found_and_missing(session):
    repo = SqlAlchemyUserRepository(session)
    await repo.create(make_new_user_entity(telegram_id=222))

    found = await repo.get_by_telegram_id(222)
    missing = await repo.get_by_telegram_id(999999)

    assert found is not None
    assert found.telegram_id == 222
    assert missing is None


async def test_get_by_id_found_and_missing(session):
    repo = SqlAlchemyUserRepository(session)
    created = await repo.create(make_new_user_entity(telegram_id=333))

    found = await repo.get_by_id(created.id)
    missing = await repo.get_by_id(created.id + 100000)

    assert found is not None
    assert missing is None


async def test_duplicate_telegram_id_returns_none_and_keeps_one_row(session):
    repo = SqlAlchemyUserRepository(session)
    first = await repo.create(make_new_user_entity(telegram_id=444, first_name="First"))

    second = await repo.create(make_new_user_entity(telegram_id=444, first_name="Second"))

    assert first is not None
    assert second is None
    assert (await session.execute(text("SELECT count(*) FROM users"))).scalar_one() == 1
    kept = await repo.get_by_telegram_id(444)
    assert kept is not None and kept.first_name == "First"  # the conflicting insert changed nothing


async def test_concurrent_inserts_of_the_same_telegram_id_produce_one_row(session):
    async def insert():
        async with db_helper.session_factory() as s:
            user = await SqlAlchemyUserRepository(s).create(make_new_user_entity(telegram_id=445))
            await s.commit()
            return user

    results = await asyncio.gather(*[insert() for _ in range(5)])

    assert sum(r is not None for r in results) == 1
    assert (await session.execute(text("SELECT count(*) FROM users"))).scalar_one() == 1


async def test_update_persists_changed_fields_and_preserves_others(session):
    repo = SqlAlchemyUserRepository(session)
    created = await repo.create(make_new_user_entity(telegram_id=555, username="old"))

    created.username = "new"
    updated = await repo.update(created)

    assert updated.username == "new"
    assert updated.telegram_id == 555
