from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.jwt_service import JWTService
from app.application.services.profile_content_validator import ProfileContentValidator
from app.application.services.telegram_init_data import TelegramInitDataValidator
from app.application.services.timezone_catalog import TimezoneCatalog
from app.application.use_cases import (
    ActivateProfileUseCase,
    AuthenticateTelegramUserUseCase,
    CreateCustomTagUseCase,
    CreateProfileUseCase,
    DeleteProfileUseCase,
    GetCategoriesUseCase,
    GetMyProfilesUseCase,
    GetProfileFormConfigUseCase,
    GetProfileUseCase,
    GetRoleFieldsByRoleUseCase,
    GetRolesByCategoryUseCase,
    PauseProfileUseCase,
    ResumeProfileUseCase,
    SuggestTagsUseCase,
    UpdateProfileUseCase,
    VerifyAccessTokenUseCase,
)
from app.core.config import settings
from app.domain.services import ExtraAttributesValidator, ProfileFormValidator, TagTitleValidator
from app.infrastructure.repositories import (
    RedisTaxonomyCacheRepository,
    SqlAlchemyProfileRepository,
    SqlAlchemyTaxonomyRepository,
    SqlAlchemyUserRepository,
)
from app.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


class Container:
    def __init__(self, session: AsyncSession, redis_client: Redis):
        self.session = session
        self.redis_client = redis_client

    # ---------- services ----------

    def telegram_init_data_service(self) -> TelegramInitDataValidator:
        return TelegramInitDataValidator(
            bot_token=settings.bot.token,
            max_age_seconds=settings.auth.init_data_ttl_seconds,
            max_future_skew_seconds=settings.auth.init_data_max_future_skew_seconds,
        )

    def jwt_service(self) -> JWTService:
        return JWTService(
            secret_key=settings.auth.secret_key,
            algorithm=settings.auth.algorithm,
            expires_minutes=settings.auth.access_token_expire_minutes,
        )

    def timezone_catalog(self) -> TimezoneCatalog:
        return TimezoneCatalog()

    def profile_content_validator(self) -> ProfileContentValidator:
        return ProfileContentValidator(
            taxonomy_repository=self.taxonomy_repo(),
            form_validator=self.profile_form_validator(),
            extra_attributes_validator=self.extra_attributes_validator(),
        )

    # ---------- unit of work ----------

    def unit_of_work(self) -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(self.session)

    # ---------- repositories ----------

    def user_repo(self) -> SqlAlchemyUserRepository:
        return SqlAlchemyUserRepository(self.session)

    def taxonomy_repo(self) -> SqlAlchemyTaxonomyRepository:
        return SqlAlchemyTaxonomyRepository(self.session, suggest_limit=settings.taxonomy.suggest_limit)

    def taxonomy_cache_repo(self) -> RedisTaxonomyCacheRepository:
        return RedisTaxonomyCacheRepository(
            redis_client=self.redis_client,
            ttl_seconds=settings.taxonomy.cache_ttl_seconds,
        )

    def profile_repo(self) -> SqlAlchemyProfileRepository:
        return SqlAlchemyProfileRepository(self.session)

    # ---------- domain services ----------

    def tag_title_validator(self) -> TagTitleValidator:
        return TagTitleValidator(
            min_length=settings.taxonomy.tag_title_min_length,
            max_length=settings.taxonomy.tag_title_max_length,
            pattern=settings.taxonomy.tag_title_allowed_pattern,
        )

    def profile_form_validator(self) -> ProfileFormValidator:
        catalog = self.timezone_catalog()
        allowed = settings.profile.allowed_country_codes
        return ProfileFormValidator(
            bio_min_length=settings.profile.bio_min_length,
            bio_max_length=settings.profile.bio_max_length,
            goals_min_length=settings.profile.goals_min_length,
            goals_max_length=settings.profile.goals_max_length,
            tags_min_count=settings.profile.tags_min_count,
            tags_max_count=settings.profile.tags_max_count,
            # Same country filter as GetProfileFormConfigUseCase, so the form offers exactly what is accepted.
            timezones_by_country={
                code: catalog.zone_ids_for(code)
                for code, _ in catalog.countries()
                if not allowed or code in allowed
            },
        )

    def extra_attributes_validator(self) -> ExtraAttributesValidator:
        return ExtraAttributesValidator()

    # ---------- use cases ----------

    def auth_use_case(self) -> AuthenticateTelegramUserUseCase:
        return AuthenticateTelegramUserUseCase(
            user_repository=self.user_repo(),
            init_data_validator=self.telegram_init_data_service(),
            jwt_service=self.jwt_service(),
            unit_of_work=self.unit_of_work(),
            profile_repository=self.profile_repo(),
        )

    def verify_access_token_use_case(self) -> VerifyAccessTokenUseCase:
        return VerifyAccessTokenUseCase(
            user_repository=self.user_repo(),
            jwt_service=self.jwt_service(),
        )

    def get_categories_use_case(self) -> GetCategoriesUseCase:
        return GetCategoriesUseCase(
            taxonomy_repository=self.taxonomy_repo(),
            taxonomy_cache_repository=self.taxonomy_cache_repo(),
        )

    def get_roles_by_category_use_case(self) -> GetRolesByCategoryUseCase:
        return GetRolesByCategoryUseCase(
            taxonomy_repository=self.taxonomy_repo(),
            taxonomy_cache_repository=self.taxonomy_cache_repo(),
        )

    def get_role_fields_by_role_use_case(self) -> GetRoleFieldsByRoleUseCase:
        return GetRoleFieldsByRoleUseCase(
            taxonomy_repository=self.taxonomy_repo(),
            taxonomy_cache_repository=self.taxonomy_cache_repo(),
        )

    def suggest_tags_use_case(self) -> SuggestTagsUseCase:
        return SuggestTagsUseCase(taxonomy_repository=self.taxonomy_repo())

    def create_custom_tag_use_case(self) -> CreateCustomTagUseCase:
        return CreateCustomTagUseCase(
            taxonomy_repository=self.taxonomy_repo(),
            tag_title_validator=self.tag_title_validator(),
            unit_of_work=self.unit_of_work(),
        )

    def get_profile_form_config_use_case(self) -> GetProfileFormConfigUseCase:
        return GetProfileFormConfigUseCase(
            profile_config=settings.profile,
            timezone_catalog=self.timezone_catalog(),
        )

    def get_my_profiles_use_case(self) -> GetMyProfilesUseCase:
        return GetMyProfilesUseCase(profile_repository=self.profile_repo())

    def get_profile_use_case(self) -> GetProfileUseCase:
        return GetProfileUseCase(profile_repository=self.profile_repo())

    def create_profile_use_case(self) -> CreateProfileUseCase:
        return CreateProfileUseCase(
            profile_repository=self.profile_repo(),
            user_repository=self.user_repo(),
            taxonomy_repository=self.taxonomy_repo(),
            profile_content_validator=self.profile_content_validator(),
            unit_of_work=self.unit_of_work(),
        )

    def update_profile_use_case(self) -> UpdateProfileUseCase:
        return UpdateProfileUseCase(
            profile_repository=self.profile_repo(),
            profile_content_validator=self.profile_content_validator(),
            unit_of_work=self.unit_of_work(),
        )

    def activate_profile_use_case(self) -> ActivateProfileUseCase:
        return ActivateProfileUseCase(
            profile_repository=self.profile_repo(),
            user_repository=self.user_repo(),
            unit_of_work=self.unit_of_work(),
        )

    def pause_profile_use_case(self) -> PauseProfileUseCase:
        return PauseProfileUseCase(
            profile_repository=self.profile_repo(),
            user_repository=self.user_repo(),
            unit_of_work=self.unit_of_work(),
        )

    def resume_profile_use_case(self) -> ResumeProfileUseCase:
        return ResumeProfileUseCase(
            profile_repository=self.profile_repo(),
            user_repository=self.user_repo(),
            unit_of_work=self.unit_of_work(),
        )

    def delete_profile_use_case(self) -> DeleteProfileUseCase:
        return DeleteProfileUseCase(
            profile_repository=self.profile_repo(),
            user_repository=self.user_repo(),
            unit_of_work=self.unit_of_work(),
        )
