from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from app.application.use_cases import EmbedProfileUseCase, SweepStaleEmbeddingsUseCase
from app.domain.entities import CategoryEntity, NewProfileEntity, ProfileEmbeddingEntity, RoleEntity, TagEntity
from app.domain.enums import EmbeddingStatus, ProfileStatus, TagStatus
from app.domain.exceptions import (
    EmbeddingProviderUnavailableError,
    EmbeddingRejectedError,
    ProfileChangedDuringEmbeddingError,
)
from app.domain.services import build_embedding_input, compute_input_hash
from tests.fixtures.fake_embedding_provider import FakeEmbeddingProvider
from tests.fixtures.fake_embedding_queue import FakeEmbeddingQueue
from tests.fixtures.fake_profile_embedding_repository import FakeProfileEmbeddingRepository
from tests.fixtures.fake_profile_repository import FakeProfileRepository
from tests.fixtures.fake_taxonomy import FakeTaxonomyRepository
from tests.fixtures.fake_unit_of_work import FakeUnitOfWork

TECH = CategoryEntity(id=1, slug="tech_product", title="Tech & Product")
ENGINEERING = RoleEntity(id=10, category_id=1, slug="engineering", title="Engineering")
TAGS = [
    TagEntity(id=1, title="python", normalized_title="python", status=TagStatus.APPROVED, created_by_user_id=None),
    TagEntity(id=2, title="fastapi", normalized_title="fastapi", status=TagStatus.APPROVED, created_by_user_id=None),
]

T0 = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)
T1 = T0 + timedelta(minutes=5)


class Env:
    def __init__(self, provider: FakeEmbeddingProvider | None = None) -> None:
        self.taxonomy = FakeTaxonomyRepository(categories=[TECH], roles=[ENGINEERING], role_fields=[], tags=TAGS)
        self.profiles = FakeProfileRepository(known_tags=TAGS)
        self.embeddings = FakeProfileEmbeddingRepository()
        self.provider = provider or FakeEmbeddingProvider()
        self.uow = FakeUnitOfWork()

    def use_case(self) -> EmbedProfileUseCase:
        return EmbedProfileUseCase(self.profiles, self.taxonomy, self.embeddings, self.provider, self.uow)

    async def add_profile(self, with_row: bool = True):
        profile = await self.profiles.create(
            NewProfileEntity(
                user_id=1,
                category_id=TECH.id,
                role_id=ENGINEERING.id,
                country_code="DE",
                timezone="Europe/Berlin",
                bio="I build backends",
                goals_description="Find a co-founder",
                extra_attributes={},
                tag_ids=[1, 2],
                status=ProfileStatus.ACTIVE,
                created_at=T0,
                updated_at=T0,
            )
        )
        if with_row:
            await self.embeddings.mark_pending(profile.id, T0)
        return profile

    async def edit_profile(self, profile, **changes):
        """Simulates an edit committed by UpdateProfileUseCase: new content, new updated_at, pending row."""
        edited = replace(profile, updated_at=T1, **changes)
        await self.profiles.update(edited, [1, 2])
        await self.embeddings.mark_pending(profile.id, T1)
        return edited

    async def row(self, profile_id: int) -> ProfileEmbeddingEntity:
        row = await self.embeddings.get(profile_id)
        assert row is not None
        return row

    def expected_text(self, bio: str = "I build backends") -> str:
        return build_embedding_input("Tech & Product", "Engineering", ["python", "fastapi"], bio, "Find a co-founder")


@pytest.fixture
def env() -> Env:
    return Env()


class TestEmbedProfile:
    async def test_missing_profile_is_ignored(self, env):
        await env.use_case().execute(999, is_last_attempt=False)

        assert env.provider.calls == []
        assert env.uow.commits == 0

    async def test_computes_the_vector_and_marks_the_row_ready(self, env):
        profile = await env.add_profile()

        await env.use_case().execute(profile.id, is_last_attempt=False)

        row = await env.row(profile.id)
        assert row.status is EmbeddingStatus.READY
        assert row.model == "fake-model"
        assert row.input_hash == compute_input_hash("fake-model", env.expected_text())
        assert env.provider.calls == [env.expected_text()]
        assert env.embeddings.vector_of(profile.id) is not None
        assert env.uow.commits == 1

    async def test_second_run_with_the_same_text_does_not_call_the_provider(self, env):
        profile = await env.add_profile()
        await env.use_case().execute(profile.id, is_last_attempt=False)
        env.uow.commits = 0

        await env.use_case().execute(profile.id, is_last_attempt=False)

        assert len(env.provider.calls) == 1
        assert env.uow.commits == 0

    async def test_edited_text_is_embedded_again(self, env):
        profile = await env.add_profile()
        await env.use_case().execute(profile.id, is_last_attempt=False)
        await env.edit_profile(profile, bio="I build mobile apps")

        await env.use_case().execute(profile.id, is_last_attempt=False)

        assert env.provider.calls[-1] == env.expected_text("I build mobile apps")
        assert len(env.provider.calls) == 2
        row = await env.row(profile.id)
        assert row.status is EmbeddingStatus.READY
        assert row.input_hash == compute_input_hash("fake-model", env.expected_text("I build mobile apps"))

    async def test_pending_row_with_an_unchanged_text_becomes_ready_without_the_provider(self, env):
        profile = await env.add_profile()
        await env.use_case().execute(profile.id, is_last_attempt=False)
        # Only the timezone changes: the text, and so the hash, stays.
        await env.edit_profile(profile, timezone="Europe/Paris")
        env.uow.commits = 0

        await env.use_case().execute(profile.id, is_last_attempt=False)

        assert len(env.provider.calls) == 1
        row = await env.row(profile.id)
        assert row.status is EmbeddingStatus.READY
        assert env.uow.commits == 1

    async def test_changed_model_is_embedded_again(self, env):
        profile = await env.add_profile()
        await env.use_case().execute(profile.id, is_last_attempt=False)
        env.provider = FakeEmbeddingProvider(model="other-model")

        await env.use_case().execute(profile.id, is_last_attempt=False)

        assert len(env.provider.calls) == 1
        row = await env.row(profile.id)
        assert (row.status, row.model) == (EmbeddingStatus.READY, "other-model")

    async def test_missing_row_is_created_and_committed_before_embedding(self, env):
        profile = await env.add_profile(with_row=False)

        await env.use_case().execute(profile.id, is_last_attempt=False)

        row = await env.row(profile.id)
        assert row.status is EmbeddingStatus.READY
        assert row.source_updated_at == profile.updated_at
        assert env.uow.commits == 2

    async def test_unavailable_provider_is_retried_before_the_last_attempt(self, env):
        profile = await env.add_profile()
        env.provider.error = EmbeddingProviderUnavailableError()

        with pytest.raises(EmbeddingProviderUnavailableError):
            await env.use_case().execute(profile.id, is_last_attempt=False)

        assert (await env.row(profile.id)).status is EmbeddingStatus.PENDING
        assert env.uow.commits == 0

    async def test_unavailable_provider_on_the_last_attempt_marks_the_row_failed(self, env):
        profile = await env.add_profile()
        env.provider.error = EmbeddingProviderUnavailableError()

        await env.use_case().execute(profile.id, is_last_attempt=True)

        assert (await env.row(profile.id)).status is EmbeddingStatus.FAILED
        assert env.uow.commits == 1

    async def test_rejected_input_fails_at_once(self, env):
        profile = await env.add_profile()
        env.provider.error = EmbeddingRejectedError()

        await env.use_case().execute(profile.id, is_last_attempt=False)

        assert (await env.row(profile.id)).status is EmbeddingStatus.FAILED
        assert env.uow.commits == 1

    async def test_failure_of_an_outdated_job_leaves_the_edited_row_pending(self, env):
        profile = await env.add_profile()

        class EditsWhileFailing(FakeEmbeddingProvider):
            async def embed(self, text: str) -> list[float]:
                await env.edit_profile(profile, bio="edited meanwhile")
                raise EmbeddingRejectedError()

        env.provider = EditsWhileFailing()

        await env.use_case().execute(profile.id, is_last_attempt=False)

        row = await env.row(profile.id)
        assert (row.status, row.source_updated_at) == (EmbeddingStatus.PENDING, T1)
        assert env.uow.commits == 0

    async def test_edit_during_embedding_discards_the_stale_vector(self, env):
        profile = await env.add_profile()

        class EditsWhileEmbedding(FakeEmbeddingProvider):
            async def embed(self, text: str) -> list[float]:
                await env.edit_profile(profile, bio="edited meanwhile")
                return await super().embed(text)

        env.provider = EditsWhileEmbedding()

        with pytest.raises(ProfileChangedDuringEmbeddingError):
            await env.use_case().execute(profile.id, is_last_attempt=False)

        row = await env.row(profile.id)
        assert (row.status, row.source_updated_at) == (EmbeddingStatus.PENDING, T1)
        assert env.embeddings.vector_of(profile.id) is None
        assert env.uow.commits == 0

    async def test_edit_after_reading_blocks_the_ready_shortcut(self, env):
        profile = await env.add_profile()
        await env.use_case().execute(profile.id, is_last_attempt=False)
        # The row moved on to a newer version that this job (reading the older profile) knows nothing about.
        await env.embeddings.mark_pending(profile.id, T1)
        env.uow.commits = 0

        with pytest.raises(ProfileChangedDuringEmbeddingError):
            await env.use_case().execute(profile.id, is_last_attempt=False)

        assert (await env.row(profile.id)).status is EmbeddingStatus.PENDING
        assert env.uow.commits == 0


def _row(profile_id: int, status: EmbeddingStatus, age: timedelta, model: str | None = "fake-model"):
    now = datetime.now(timezone.utc)
    return ProfileEmbeddingEntity(
        profile_id=profile_id,
        input_hash="hash",
        model=model,
        status=status,
        source_updated_at=T0,
        updated_at=now - age,
    )


class RecordingQueue(FakeEmbeddingQueue):
    """Remembers how many commits had happened when each job was enqueued."""

    def __init__(self, uow: FakeUnitOfWork) -> None:
        super().__init__()
        self._uow = uow
        self.commits_at_enqueue: list[int] = []

    async def enqueue(self, profile_id: int) -> None:
        self.commits_at_enqueue.append(self._uow.commits)
        await super().enqueue(profile_id)


class TestSweepStaleEmbeddings:
    def _use_case(self, rows, batch_size: int = 100, provider: FakeEmbeddingProvider | None = None):
        self.embeddings = FakeProfileEmbeddingRepository(rows)
        self.uow = FakeUnitOfWork()
        self.queue = RecordingQueue(self.uow)
        return SweepStaleEmbeddingsUseCase(
            self.embeddings,
            provider or FakeEmbeddingProvider(),
            self.queue,
            self.uow,
            pending_after_seconds=300,
            failed_after_seconds=3600,
            batch_size=batch_size,
        )

    async def test_claims_only_stale_rows(self):
        use_case = self._use_case(
            [
                _row(1, EmbeddingStatus.PENDING, timedelta(minutes=10)),
                _row(2, EmbeddingStatus.PENDING, timedelta(minutes=1)),
                _row(3, EmbeddingStatus.FAILED, timedelta(hours=2)),
                _row(4, EmbeddingStatus.FAILED, timedelta(minutes=10)),
                _row(5, EmbeddingStatus.READY, timedelta(days=1)),
            ]
        )

        claimed = await use_case.execute()

        assert claimed == 2
        assert sorted(self.queue.enqueued) == [1, 3]

    async def test_ready_row_of_another_model_is_claimed(self):
        use_case = self._use_case([_row(1, EmbeddingStatus.READY, timedelta(days=1), model="old-model")])

        assert await use_case.execute() == 1
        assert self.queue.enqueued == [1]

    async def test_claimed_rows_are_not_claimed_again(self):
        use_case = self._use_case([_row(1, EmbeddingStatus.PENDING, timedelta(minutes=10))])

        await use_case.execute()
        await use_case.execute()

        assert self.queue.enqueued == [1]

    async def test_respects_the_batch_size_and_takes_the_oldest_first(self):
        use_case = self._use_case(
            [
                _row(1, EmbeddingStatus.PENDING, timedelta(minutes=10)),
                _row(2, EmbeddingStatus.PENDING, timedelta(minutes=30)),
                _row(3, EmbeddingStatus.PENDING, timedelta(minutes=20)),
            ],
            batch_size=2,
        )

        assert await use_case.execute() == 2
        assert self.queue.enqueued == [2, 3]

    async def test_commits_the_claim_before_enqueueing(self):
        use_case = self._use_case(
            [
                _row(1, EmbeddingStatus.PENDING, timedelta(minutes=10)),
                _row(2, EmbeddingStatus.PENDING, timedelta(minutes=11)),
            ]
        )

        await use_case.execute()

        assert self.queue.commits_at_enqueue == [1, 1]

    async def test_nothing_to_do(self):
        use_case = self._use_case([_row(1, EmbeddingStatus.READY, timedelta(days=1))])

        assert await use_case.execute() == 0
        assert self.queue.enqueued == []
