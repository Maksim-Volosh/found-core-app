from app.domain.interfaces import IUnitOfWork


class FakeUnitOfWork(IUnitOfWork):
    """Counts commits so unit tests can assert that a use case committed exactly
    once on success and never on failure."""

    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1
