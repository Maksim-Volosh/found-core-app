import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.domain.constants import EMBEDDING_DIMENSIONS
from app.domain.entities import ProfileEntity
from app.domain.enums import EmbeddingStatus
from app.infrastructure.helpers import db_helper
from app.infrastructure.models import ProfileEmbeddingModel
from app.infrastructure.repositories import SqlAlchemyProfileEmbeddingRepository, SqlAlchemyProfileRepository
from tests.fixtures.auth import create_user_with_headers
from tests.fixtures.factories import make_new_profile_entity
from tests.fixtures.taxonomy_data import add_tag

# Multiples of 1/8 are exact in float32, so the vector survives the round trip unchanged.
VECTOR = [(i % 8) / 8 for i in range(EMBEDDING_DIMENSIONS)]
OTHER_VECTOR = [((i + 1) % 8) / 8 for i in range(EMBEDDING_DIMENSIONS)]


async def _create_profiles(session, taxonomy_data, count: int) -> list[ProfileEntity]:
    """One profile per user, each in the same role; returns them in creation order."""
    t = taxonomy_data
    tags = [
        await add_tag(session, f"tag-{i}", scopes=[(t.tech_category_id, t.engineering_role_id)])
        for i in range(5)
    ]
    repo = SqlAlchemyProfileRepository(session)
    profiles = []
    for telegram_id in range(1, count + 1):
        user, _ = await create_user_with_headers(session, telegram_id=telegram_id)
        profile = await repo.create(
            make_new_profile_entity(
                user_id=user.id,
                category_id=t.tech_category_id,
                role_id=t.engineering_role_id,
                tag_ids=[tag.id for tag in tags],
            )
        )
        profiles.append(profile)
    await session.commit()
    return profiles


async def _stored_vector(session, profile_id: int) -> list[float] | None:
    stmt = select(ProfileEmbeddingModel.embedding).where(ProfileEmbeddingModel.profile_id == profile_id)
    return (await session.execute(stmt)).scalar_one()


async def _set_updated_at(session, profile_id: int, updated_at: datetime) -> None:
    await session.execute(
        text("UPDATE profile_embeddings SET updated_at = :t WHERE profile_id = :id"),
        {"t": updated_at, "id": profile_id},
    )
    await session.commit()


async def _ready_row(session, profile: ProfileEntity, model: str = "model-a") -> SqlAlchemyProfileEmbeddingRepository:
    repo = SqlAlchemyProfileEmbeddingRepository(session)
    await repo.mark_pending(profile.id, profile.updated_at)
    assert await repo.save(profile.id, VECTOR, "hash", model, profile.updated_at)
    await session.commit()
    return repo


async def test_get_returns_none_for_a_profile_without_a_row(session, taxonomy_data):
    assert await SqlAlchemyProfileEmbeddingRepository(session).get(1) is None


async def test_mark_pending_creates_a_pending_row_without_a_vector(session, taxonomy_data):
    (profile,) = await _create_profiles(session, taxonomy_data, 1)
    repo = SqlAlchemyProfileEmbeddingRepository(session)

    await repo.mark_pending(profile.id, profile.updated_at)
    await session.commit()

    row = await repo.get(profile.id)
    assert row.status is EmbeddingStatus.PENDING
    assert row.source_updated_at == profile.updated_at
    assert (row.input_hash, row.model) == (None, None)
    assert await _stored_vector(session, profile.id) is None


async def test_mark_pending_keeps_the_vector_of_an_existing_row(session, taxonomy_data):
    (profile,) = await _create_profiles(session, taxonomy_data, 1)
    repo = await _ready_row(session, profile)
    edited_at = profile.updated_at + timedelta(seconds=5)

    await repo.mark_pending(profile.id, edited_at)
    await session.commit()

    row = await repo.get(profile.id)
    assert row.status is EmbeddingStatus.PENDING
    assert row.source_updated_at == edited_at
    assert (row.input_hash, row.model) == ("hash", "model-a")
    assert await _stored_vector(session, profile.id) == VECTOR


async def test_save_stores_a_full_size_vector_and_marks_the_row_ready(session, taxonomy_data):
    (profile,) = await _create_profiles(session, taxonomy_data, 1)
    repo = SqlAlchemyProfileEmbeddingRepository(session)
    await repo.mark_pending(profile.id, profile.updated_at)

    saved = await repo.save(profile.id, VECTOR, "hash", "model-a", profile.updated_at)
    await session.commit()

    assert saved is True
    row = await repo.get(profile.id)
    assert (row.status, row.input_hash, row.model) == (EmbeddingStatus.READY, "hash", "model-a")
    assert await _stored_vector(session, profile.id) == VECTOR


async def test_save_refuses_a_profile_edited_after_it_was_read(session, taxonomy_data):
    (profile,) = await _create_profiles(session, taxonomy_data, 1)
    repo = SqlAlchemyProfileEmbeddingRepository(session)
    await repo.mark_pending(profile.id, profile.updated_at + timedelta(seconds=5))

    saved = await repo.save(profile.id, VECTOR, "hash", "model-a", profile.updated_at)
    await session.commit()

    assert saved is False
    row = await repo.get(profile.id)
    assert row.status is EmbeddingStatus.PENDING
    assert await _stored_vector(session, profile.id) is None


async def test_save_returns_false_for_a_missing_row(session, taxonomy_data):
    (profile,) = await _create_profiles(session, taxonomy_data, 1)

    saved = await SqlAlchemyProfileEmbeddingRepository(session).save(
        profile.id, VECTOR, "hash", "model-a", profile.updated_at
    )

    assert saved is False


async def test_save_rejects_a_vector_of_the_wrong_length(session, taxonomy_data):
    (profile,) = await _create_profiles(session, taxonomy_data, 1)
    repo = SqlAlchemyProfileEmbeddingRepository(session)
    await repo.mark_pending(profile.id, profile.updated_at)

    with pytest.raises(DBAPIError):
        await repo.save(profile.id, [0.1] * 3, "hash", "model-a", profile.updated_at)


async def test_set_outcome_changes_only_the_status(session, taxonomy_data):
    (profile,) = await _create_profiles(session, taxonomy_data, 1)
    repo = await _ready_row(session, profile)

    changed = await repo.set_outcome(profile.id, EmbeddingStatus.FAILED, profile.updated_at)
    await session.commit()

    assert changed is True
    row = await repo.get(profile.id)
    assert (row.status, row.input_hash, row.model) == (EmbeddingStatus.FAILED, "hash", "model-a")
    assert await _stored_vector(session, profile.id) == VECTOR


async def test_set_outcome_refuses_a_profile_edited_after_it_was_read(session, taxonomy_data):
    (profile,) = await _create_profiles(session, taxonomy_data, 1)
    repo = SqlAlchemyProfileEmbeddingRepository(session)
    await repo.mark_pending(profile.id, profile.updated_at + timedelta(seconds=5))

    changed = await repo.set_outcome(profile.id, EmbeddingStatus.READY, profile.updated_at)
    await session.commit()

    assert changed is False
    assert (await repo.get(profile.id)).status is EmbeddingStatus.PENDING


async def test_a_write_waiting_for_a_concurrent_edit_loses_the_race(session, taxonomy_data):
    (profile,) = await _create_profiles(session, taxonomy_data, 1)
    await SqlAlchemyProfileEmbeddingRepository(session).mark_pending(profile.id, profile.updated_at)
    await session.commit()
    edited_at = profile.updated_at + timedelta(seconds=5)

    async with db_helper.session_factory() as editor, db_helper.session_factory() as worker:
        # The edit holds the row lock until it commits.
        await SqlAlchemyProfileEmbeddingRepository(editor).mark_pending(profile.id, edited_at)
        save = asyncio.create_task(
            SqlAlchemyProfileEmbeddingRepository(worker).save(
                profile.id, VECTOR, "hash", "model-a", profile.updated_at
            )
        )
        await asyncio.sleep(0.3)
        assert not save.done()

        await editor.commit()
        saved = await save
        await worker.commit()

    assert saved is False
    row = await SqlAlchemyProfileEmbeddingRepository(session).get(profile.id)
    assert (row.status, row.source_updated_at) == (EmbeddingStatus.PENDING, edited_at)
    assert await _stored_vector(session, profile.id) is None


async def test_claim_stale_selects_rows_by_status_age_and_model(session, taxonomy_data):
    profiles = await _create_profiles(session, taxonomy_data, 6)
    pending_old, pending_fresh, failed_old, failed_fresh, ready_same, ready_other = profiles
    repo = SqlAlchemyProfileEmbeddingRepository(session)
    for profile in profiles:
        await repo.mark_pending(profile.id, profile.updated_at)
    for profile, outcome in ((failed_old, EmbeddingStatus.FAILED), (failed_fresh, EmbeddingStatus.FAILED)):
        await repo.set_outcome(profile.id, outcome, profile.updated_at)
    for profile, model in ((ready_same, "current"), (ready_other, "previous")):
        await repo.save(profile.id, VECTOR, "hash", model, profile.updated_at)
    await session.commit()
    now = datetime.now(timezone.utc)
    ages = [
        (pending_old, timedelta(minutes=10)),
        (pending_fresh, timedelta(minutes=1)),
        (failed_old, timedelta(hours=2)),
        (failed_fresh, timedelta(minutes=30)),
        (ready_same, timedelta(days=1)),
        (ready_other, timedelta(days=1)),
    ]
    for profile, age in ages:
        await _set_updated_at(session, profile.id, now - age)

    claimed = await repo.claim_stale(
        pending_before=now - timedelta(minutes=5),
        failed_before=now - timedelta(hours=1),
        model="current",
        limit=100,
    )

    assert claimed == sorted([pending_old.id, failed_old.id, ready_other.id])


async def test_claim_stale_respects_the_limit_and_takes_the_oldest_first(session, taxonomy_data):
    profiles = await _create_profiles(session, taxonomy_data, 3)
    repo = SqlAlchemyProfileEmbeddingRepository(session)
    now = datetime.now(timezone.utc)
    for profile, age in zip(profiles, (timedelta(hours=1), timedelta(hours=3), timedelta(hours=2))):
        await repo.mark_pending(profile.id, profile.updated_at)
        await session.commit()
        await _set_updated_at(session, profile.id, now - age)

    claimed = await repo.claim_stale(now, now, "current", limit=2)

    assert claimed == sorted([profiles[1].id, profiles[2].id])


async def test_claimed_rows_are_not_claimed_again(session, taxonomy_data):
    (profile,) = await _create_profiles(session, taxonomy_data, 1)
    repo = SqlAlchemyProfileEmbeddingRepository(session)
    await repo.mark_pending(profile.id, profile.updated_at)
    await session.commit()
    await _set_updated_at(session, profile.id, datetime.now(timezone.utc) - timedelta(hours=1))
    threshold = datetime.now(timezone.utc) - timedelta(minutes=5)

    first = await repo.claim_stale(threshold, threshold, "current", limit=10)
    await session.commit()
    second = await repo.claim_stale(threshold, threshold, "current", limit=10)

    assert first == [profile.id]
    assert second == []


async def test_concurrent_claims_never_return_the_same_row(session, taxonomy_data):
    profiles = await _create_profiles(session, taxonomy_data, 6)
    repo = SqlAlchemyProfileEmbeddingRepository(session)
    for profile in profiles:
        await repo.mark_pending(profile.id, profile.updated_at)
    await session.commit()
    old = datetime.now(timezone.utc) - timedelta(hours=1)
    for profile in profiles:
        await _set_updated_at(session, profile.id, old)
    threshold = datetime.now(timezone.utc) - timedelta(minutes=5)

    async with db_helper.session_factory() as first, db_helper.session_factory() as second:
        # Neither transaction has committed, so the first one still holds the locks of its rows.
        claimed_first = await SqlAlchemyProfileEmbeddingRepository(first).claim_stale(
            threshold, threshold, "current", limit=4
        )
        claimed_second = await SqlAlchemyProfileEmbeddingRepository(second).claim_stale(
            threshold, threshold, "current", limit=4
        )
        await first.commit()
        await second.commit()

    assert len(claimed_first) == 4
    assert len(claimed_second) == 2
    assert set(claimed_first).isdisjoint(claimed_second)


async def test_deleting_a_profile_deletes_its_row(session, taxonomy_data):
    (profile,) = await _create_profiles(session, taxonomy_data, 1)
    repo = SqlAlchemyProfileEmbeddingRepository(session)
    await repo.mark_pending(profile.id, profile.updated_at)
    await session.commit()

    await SqlAlchemyProfileRepository(session).delete(profile.id)
    await session.commit()

    assert await repo.get(profile.id) is None
