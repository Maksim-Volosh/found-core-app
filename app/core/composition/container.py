from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.jwt_service import JWTService
from app.application.services.telegram_init_data import TelegramInitDataValidator
from app.application.use_cases import AuthenticateTelegramUserUseCase, VerifyAccessTokenUseCase
from app.core.config import settings
from app.infrastructure.repositories import SqlAlchemyUserRepository


class Container:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ---------- services ----------

    def telegram_init_data_service(self) -> TelegramInitDataValidator:
        return TelegramInitDataValidator(
            bot_token=settings.bot.token,
            max_age_seconds=settings.auth.init_data_ttl_seconds,
        )

    def jwt_service(self) -> JWTService:
        return JWTService(
            secret_key=settings.auth.secret_key,
            algorithm=settings.auth.algorithm,
            expires_minutes=settings.auth.access_token_expire_minutes,
        )

    # ---------- repositories ----------

    def user_repo(self) -> SqlAlchemyUserRepository:
        return SqlAlchemyUserRepository(self.session)

    # ---------- use cases ----------

    def auth_use_case(self) -> AuthenticateTelegramUserUseCase:
        return AuthenticateTelegramUserUseCase(
            user_repository=self.user_repo(),
            init_data_validator=self.telegram_init_data_service(),
            jwt_service=self.jwt_service(),
        )

    def verify_access_token_use_case(self) -> VerifyAccessTokenUseCase:
        return VerifyAccessTokenUseCase(
            user_repository=self.user_repo(),
            jwt_service=self.jwt_service(),
        )
