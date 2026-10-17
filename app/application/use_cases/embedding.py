from datetime import datetime, timedelta, timezone

from app.domain.enums import EmbeddingStatus
from app.domain.exceptions import (
    EmbeddingProviderUnavailableError,
    EmbeddingRejectedError,
    ProfileChangedDuringEmbeddingError,
)
from app.domain.interfaces import (
    IEmbeddingJobQueue,
    IEmbeddingProvider,
    IProfileEmbeddingRepository,
    IProfileRepository,
    ITaxonomyRepository,
    IUnitOfWork,
)
from app.domain.services import build_embedding_input, compute_input_hash


class EmbedProfileUseCase:
    def __init__(
        self,
        profile_repository: IProfileRepository,
        taxonomy_repository: ITaxonomyRepository,
        profile_embedding_repository: IProfileEmbeddingRepository,
        embedding_provider: IEmbeddingProvider,
        unit_of_work: IUnitOfWork,
    ) -> None:
        self._profile_repository = profile_repository
        self._taxonomy_repository = taxonomy_repository
        self._profile_embedding_repository = profile_embedding_repository
        self._embedding_provider = embedding_provider
        self._unit_of_work = unit_of_work

    async def execute(self, profile_id: int, is_last_attempt: bool) -> None:
        profile = await self._profile_repository.get_by_id(profile_id)
        if profile is None:
            # Deleted while the job was waiting; the embedding row went with it.
            return

        state = await self._profile_embedding_repository.get(profile_id)
        if state is None:
            # Not expected: the row is created together with the profile. It is committed right away
            # (the only place where a use case commits twice), otherwise a crash before the final commit would
            # roll the row back, and the sweep, which only looks at this table, would never find the profile.
            await self._profile_embedding_repository.mark_pending(profile_id, profile.updated_at)
            await self._unit_of_work.commit()
            state = await self._profile_embedding_repository.get(profile_id)
            assert state is not None

        category = await self._taxonomy_repository.get_category_by_id(profile.category_id)
        role = await self._taxonomy_repository.get_role_by_id(profile.role_id)
        # Taxonomy rows that profiles reference cannot be deleted (no ON DELETE on the foreign keys).
        assert category is not None and role is not None
        text = build_embedding_input(
            category.title,
            role.title,
            [tag.title for tag in profile.tags],
            profile.bio,
            profile.goals_description,
        )
        # The hash covers the model name, so a match also means the vector comes from the current model.
        input_hash = compute_input_hash(self._embedding_provider.model, text)
        # Every write below is conditional on the profile still having this `updated_at`.
        expected = profile.updated_at

        if state.input_hash == input_hash:
            if state.status is EmbeddingStatus.READY:
                return
            # The text did not change (for example only the timezone was edited): the stored vector is still valid.
            if not await self._profile_embedding_repository.set_outcome(
                profile_id, EmbeddingStatus.READY, expected
            ):
                raise ProfileChangedDuringEmbeddingError()
            await self._unit_of_work.commit()
            return

        try:
            vector = await self._embedding_provider.embed(text)
        except (EmbeddingProviderUnavailableError, EmbeddingRejectedError) as error:
            if isinstance(error, EmbeddingProviderUnavailableError) and not is_last_attempt:
                raise
            # A permanent failure, or the retries are used up. If the profile was edited meanwhile, the row is
            # already pending again with a newer `source_updated_at` and the edit has its own job.
            if await self._profile_embedding_repository.set_outcome(profile_id, EmbeddingStatus.FAILED, expected):
                await self._unit_of_work.commit()
            return

        if not await self._profile_embedding_repository.save(
            profile_id, vector, input_hash, self._embedding_provider.model, expected
        ):
            raise ProfileChangedDuringEmbeddingError()
        await self._unit_of_work.commit()


class SweepStaleEmbeddingsUseCase:
    def __init__(
        self,
        profile_embedding_repository: IProfileEmbeddingRepository,
        embedding_provider: IEmbeddingProvider,
        embedding_queue: IEmbeddingJobQueue,
        unit_of_work: IUnitOfWork,
        pending_after_seconds: int,
        failed_after_seconds: int,
        batch_size: int,
    ) -> None:
        self._profile_embedding_repository = profile_embedding_repository
        self._embedding_provider = embedding_provider
        self._embedding_queue = embedding_queue
        self._unit_of_work = unit_of_work
        self._pending_after = timedelta(seconds=pending_after_seconds)
        self._failed_after = timedelta(seconds=failed_after_seconds)
        self._batch_size = batch_size

    async def execute(self) -> int:
        now = datetime.now(timezone.utc)
        profile_ids = await self._profile_embedding_repository.claim_stale(
            pending_before=now - self._pending_after,
            failed_before=now - self._failed_after,
            model=self._embedding_provider.model,
            limit=self._batch_size,
        )
        # Committed before enqueueing, so the claim is visible to a concurrent sweep and to the jobs themselves.
        await self._unit_of_work.commit()
        for profile_id in profile_ids:
            await self._embedding_queue.enqueue(profile_id)
        return len(profile_ids)
