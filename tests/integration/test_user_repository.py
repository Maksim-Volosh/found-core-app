import pytest
from sqlalchemy.exc import IntegrityError

from app.infrastructure.repositories.user import SqlAlchemyUserRepository
from tests.fixtures.factories import make_new_user_entity


async def test_create_persists_and_assigns_defaults(session):
    repo = SqlAlchemyUserRepository(session)

    entity = await repo.create(make_new_user_entity(telegram_id=111))

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


async def test_duplicate_telegram_id_raises_integrity_error(session):
    repo = SqlAlchemyUserRepository(session)
    await repo.create(make_new_user_entity(telegram_id=444))

    with pytest.raises(IntegrityError):
        await repo.create(make_new_user_entity(telegram_id=444))


async def test_update_persists_changed_fields_and_preserves_others(session):
    repo = SqlAlchemyUserRepository(session)
    created = await repo.create(make_new_user_entity(telegram_id=555, username="old"))

    created.username = "new"
    updated = await repo.update(created)

    assert updated.username == "new"
    assert updated.telegram_id == 555
