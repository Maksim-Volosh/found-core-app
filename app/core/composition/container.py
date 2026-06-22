from sqlalchemy.ext.asyncio import AsyncSession

from app.application.use_cases import UserAuthUseCase, UserUseCase
from app.core.config import settings
from app.infrastructure.repositories import SQLAlchemyUserRepository
from app.infrastructure.repositories.subscription import SQLAlchemySubscriptionRepository


class Container:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ---------- repositories ----------

    def user_repo(self):
        return SQLAlchemyUserRepository(self.session)

    def subscription_repo(self):
        return SQLAlchemySubscriptionRepository(self.session)

    # ---------- use cases ----------

    def user_use_case(self):
        return UserUseCase(repo=self.user_repo())
    
    def user_auth_use_case(self):
        return UserAuthUseCase(user_repo=self.user_repo(), subscription_repo=self.subscription_repo())