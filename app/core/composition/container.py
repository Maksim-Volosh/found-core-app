from sqlalchemy.ext.asyncio import AsyncSession

from app.application.use_cases import (
    UserUseCase,
)
from app.core.config import settings
from app.infrastructure.repositories import (
    SQLAlchemyUserRepository,
)


class Container:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ---------- repositories ----------

    def user_repo(self):
        return SQLAlchemyUserRepository(self.session)

    # ---------- use cases ----------

    def user_use_case(self):
        return UserUseCase(repo=self.user_repo())