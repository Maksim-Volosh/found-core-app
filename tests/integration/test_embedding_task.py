"""The worker side against real Postgres: the async cores of the tasks use their own engine, as in production."""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from app.core.config import settings
from app.domain.constants import EMBEDDING_DIMENSIONS
from app.infrastructure.providers import StubEmbeddingProvider
from app.infrastructure.repositories import SqlAlchemyProfileEmbeddingRepository, SqlAlchemyProfileRepository
from app.worker.tasks import embed_profile, run_embed_profile, run_sweep_stale_embeddings
from tests.fixtures.auth import create_user_with_headers
from tests.fixtures.factories import make_new_profile_entity
from tests.fixtures.taxonomy_data import add_tag

STUB_MODEL = StubEmbeddingProvider().model


@pytest.fixture(autouse=True)
def _patient_enqueue(monkeypatch) -> None:
    # The sweep enqueues through the real queue; the production timeout is short on purpose, and a slow first
    # connection on a developer machine must not make these tests flaky.
    monkeypatch.setattr(settings.embedding, "enqueue_timeout_seconds", 5.0)


async def _create_pending_profile(session, taxonomy_data, telegram_id: int = 1):
    """A profile with a pending embedding row, the way CreateProfileUseCase leaves it."""
    t = taxonomy_data
    scope = [(t.tech_category_id, t.engineering_role_id)]
    tags = [await add_tag(session, f"tag-{telegram_id}-{i}", scopes=scope) for i in range(5)]
    user, _ = await create_user_with_headers(session, telegram_id=telegram_id)
    profile = await SqlAlchemyProfileRepository(session).create(
        make_new_profile_entity(
            user_id=user.id,
            category_id=t.tech_category_id,
            role_id=t.engineering_role_id,
            tag_ids=[tag.id for tag in tags],
        )
    )
    await SqlAlchemyProfileEmbeddingRepository(session).mark_pending(profile.id, profile.updated_at)
    await session.commit()
    return profile


async def _row(session, profile_id: int):
    result = await session.execute(
        text(
            "SELECT status, model, input_hash, updated_at, vector_dims(embedding) AS dims "
            "FROM profile_embeddings WHERE profile_id = :id"
        ),
        {"id": profile_id},
    )
    row = result.one_or_none()
    await session.rollback()
    return row


async def _age(session, profile_id: int, by: timedelta) -> None:
    await session.execute(
        text("UPDATE profile_embeddings SET updated_at = :t WHERE profile_id = :id"),
        {"t": datetime.now(timezone.utc) - by, "id": profile_id},
    )
    await session.commit()


class TestRunEmbedProfile:
    async def test_computes_the_vector_and_marks_the_row_ready(self, session, taxonomy_data):
        profile = await _create_pending_profile(session, taxonomy_data)

        await run_embed_profile(profile.id, is_last_attempt=False)

        row = await _row(session, profile.id)
        assert (row.status, row.model, row.dims) == ("ready", STUB_MODEL, EMBEDDING_DIMENSIONS)
        assert row.input_hash is not None

    async def test_a_second_run_with_the_same_text_changes_nothing(self, session, taxonomy_data):
        profile = await _create_pending_profile(session, taxonomy_data)
        await run_embed_profile(profile.id, is_last_attempt=False)
        before = await _row(session, profile.id)

        await run_embed_profile(profile.id, is_last_attempt=False)

        assert await _row(session, profile.id) == before

    async def test_a_deleted_profile_is_ignored(self, session, taxonomy_data):
        await run_embed_profile(999, is_last_attempt=False)

        assert await _row(session, 999) is None


class TestEmbedProfileTask:
    async def test_the_celery_task_runs_the_whole_path(self, session, taxonomy_data):
        profile = await _create_pending_profile(session, taxonomy_data)

        # The task starts its own event loop, so it cannot run inside the test's one: a thread of its own.
        result = await asyncio.to_thread(embed_profile.apply, args=[profile.id])

        assert result.successful()
        assert (await _row(session, profile.id)).status == "ready"


class TestSweep:
    async def test_re_enqueues_only_stale_pending_rows(self, session, taxonomy_data, broker_client):
        stale = await _create_pending_profile(session, taxonomy_data, telegram_id=1)
        fresh = await _create_pending_profile(session, taxonomy_data, telegram_id=2)
        await _age(session, stale.id, timedelta(hours=1))

        claimed = await run_sweep_stale_embeddings()

        assert claimed == 1
        assert await broker_client.llen("embeddings") == 1
        assert (await _row(session, fresh.id)).status == "pending"

    async def test_a_claimed_row_is_not_claimed_again_at_once(self, session, taxonomy_data, broker_client):
        profile = await _create_pending_profile(session, taxonomy_data)
        await _age(session, profile.id, timedelta(hours=1))

        assert await run_sweep_stale_embeddings() == 1
        assert await run_sweep_stale_embeddings() == 0
        assert await broker_client.llen("embeddings") == 1
