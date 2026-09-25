from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.jwt_service import JWTService
from app.application.services.telegram_init_data import TelegramInitDataValidator
from app.application.use_cases import (
    AuthenticateTelegramUserUseCase,
    CreateCustomTagUseCase,
    GetCategoriesUseCase,
    GetRoleFieldsByRoleUseCase,
    GetRolesByCategoryUseCase,
    SuggestTagsUseCase,
    VerifyAccessTokenUseCase,
)
from app.core.config import settings
from app.infrastructure.repositories import SqlAlchemyTaxonomyRepository, SqlAlchemyUserRepository


class Container:
    def __init__(self, session: AsyncSession, redis_client: Redis):
        self.session = session
        self.redis_client = redis_client

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

    def taxonomy_repo(self) -> SqlAlchemyTaxonomyRepository:
        return SqlAlchemyTaxonomyRepository(self.session, self.redis_client)

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

    def get_categories_use_case(self) -> GetCategoriesUseCase:
        return GetCategoriesUseCase(taxonomy_repository=self.taxonomy_repo())

    def get_roles_by_category_use_case(self) -> GetRolesByCategoryUseCase:
        return GetRolesByCategoryUseCase(taxonomy_repository=self.taxonomy_repo())

    def get_role_fields_by_role_use_case(self) -> GetRoleFieldsByRoleUseCase:
        return GetRoleFieldsByRoleUseCase(taxonomy_repository=self.taxonomy_repo())

    def suggest_tags_use_case(self) -> SuggestTagsUseCase:
        return SuggestTagsUseCase(taxonomy_repository=self.taxonomy_repo())

    def create_custom_tag_use_case(self) -> CreateCustomTagUseCase:
        return CreateCustomTagUseCase(taxonomy_repository=self.taxonomy_repo())
