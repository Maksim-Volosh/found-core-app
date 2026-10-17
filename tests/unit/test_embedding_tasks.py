import pytest

from app.core.config import settings
from app.domain.exceptions import EmbeddingProviderUnavailableError, ProfileChangedDuringEmbeddingError
from app.worker import tasks

ATTEMPTS = settings.embedding.task_max_retries + 1


@pytest.fixture
def attempts(monkeypatch) -> list[tuple[int, bool]]:
    """Replaces the async core of the task and records (profile_id, is_last_attempt) of every attempt."""
    calls: list[tuple[int, bool]] = []

    async def fake(profile_id: int, is_last_attempt: bool) -> None:
        calls.append((profile_id, is_last_attempt))
        # What the real use case does: an unavailable provider is retried until the last attempt.
        if not is_last_attempt:
            raise EmbeddingProviderUnavailableError()

    monkeypatch.setattr(tasks, "run_embed_profile", fake)
    return calls


class TestEmbedProfileTask:
    def test_retries_until_the_last_attempt_and_flags_only_that_one(self, attempts):
        result = tasks.embed_profile.apply(args=[7])

        assert result.successful()
        assert attempts == [(7, False)] * settings.embedding.task_max_retries + [(7, True)]

    def test_success_on_the_first_attempt_is_not_retried(self, monkeypatch):
        calls: list[bool] = []

        async def fake(profile_id: int, is_last_attempt: bool) -> None:
            calls.append(is_last_attempt)

        monkeypatch.setattr(tasks, "run_embed_profile", fake)

        assert tasks.embed_profile.apply(args=[7]).successful()
        assert calls == [False]

    def test_a_concurrent_edit_is_retried_and_then_left_to_the_sweep(self, monkeypatch):
        calls: list[bool] = []

        async def fake(profile_id: int, is_last_attempt: bool) -> None:
            calls.append(is_last_attempt)
            raise ProfileChangedDuringEmbeddingError()

        monkeypatch.setattr(tasks, "run_embed_profile", fake)

        result = tasks.embed_profile.apply(args=[7])

        assert result.failed()
        # Celery cannot unpickle exceptions whose constructor takes no arguments and wraps them.
        assert result.result.exc_cls_name == ProfileChangedDuringEmbeddingError.__name__
        assert len(calls) == ATTEMPTS

    def test_other_errors_are_not_retried(self, monkeypatch):
        calls: list[bool] = []

        async def fake(profile_id: int, is_last_attempt: bool) -> None:
            calls.append(is_last_attempt)
            raise RuntimeError("boom")

        monkeypatch.setattr(tasks, "run_embed_profile", fake)

        result = tasks.embed_profile.apply(args=[7])

        assert result.failed()
        assert calls == [False]


class TestSweepTask:
    def test_runs_the_sweep(self, monkeypatch):
        calls: list[str] = []

        async def fake() -> int:
            calls.append("sweep")
            return 3

        monkeypatch.setattr(tasks, "run_sweep_stale_embeddings", fake)

        assert tasks.sweep_stale_embeddings.apply().successful()
        assert calls == ["sweep"]
