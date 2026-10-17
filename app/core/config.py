from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, PostgresDsn, RedisDsn, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Public placeholders from .env.template / .env.test; a production deployment must never run with them.
_PLACEHOLDER_SECRET_KEYS = frozenset({"", "dev-only-insecure-secret-change-me", "change-me", "secret"})
_PLACEHOLDER_BOT_TOKENS = frozenset({"", "key", "123"})
_MIN_PROD_SECRET_KEY_LENGTH = 32


class RunConfig(BaseModel):
    # Plain BaseModel, not BaseSettings: the default `RunConfig()` instance would otherwise read unprefixed
    # environment variables, and a generic name like ENV is often already set in the shell.
    env: Literal["dev", "test", "prod"] = "dev"
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True


class DetailsConfig(BaseModel):
    title: str = "FoundCore API"
    description: str = "API"


class ApiConfig(BaseModel):
    prefix: str = "/api"


class DatabaseConfig(BaseSettings):
    url: PostgresDsn
    echo: bool = False
    echo_pool: bool = False
    pool_size: int = 50
    max_overflow: int = 10

    naming_convention: dict[str, str] = {
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }


class RedisConfig(BaseSettings):
    url: RedisDsn
    socket_timeout: float = 0.3


class BotConfig(BaseSettings):
    token: str


class AuthConfig(BaseSettings):
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    init_data_ttl_seconds: int = 300
    init_data_max_future_skew_seconds: int = 60


class TaxonomyConfig(BaseSettings):
    tag_title_min_length: int = 1
    tag_title_max_length: int = 64
    tag_title_allowed_pattern: str = r"[\w\s+#./-]+"
    cache_ttl_seconds: int = 21600
    suggest_limit: int = 20


class ProfileConfig(BaseModel):
    # Plain BaseModel for the same reason as RunConfig: the default instance must not read unprefixed env variables.
    bio_min_length: int = 200
    bio_max_length: int = 2000
    goals_min_length: int = 200
    goals_max_length: int = 2000
    tags_min_count: int = 5
    tags_max_count: int = 15
    # Empty means every ISO 3166 country that has at least one timezone is allowed.
    allowed_country_codes: list[str] = []


class EmbeddingConfig(BaseModel):
    # Plain BaseModel for the same reason as RunConfig. `broker_url` has no default and no fallback to `redis.url`,
    # so the Celery broker can never end up in the logical Redis DB that holds the cache by accident.
    provider: Literal["stub", "openai"] = "stub"
    broker_url: str
    openai_api_key: SecretStr | None = None
    model: str = "text-embedding-3-small"
    openai_base_url: str = "https://api.openai.com/v1"
    request_timeout_seconds: float = 10.0
    enqueue_timeout_seconds: float = 0.5
    queue_name: str = "embeddings"
    task_max_retries: int = 5
    task_time_limit_seconds: int = 60
    retry_base_delay_seconds: int = 5
    sweep_interval_seconds: int = 600
    sweep_pending_after_seconds: int = 300
    sweep_failed_after_seconds: int = 3600
    sweep_batch_size: int = 100


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env",),
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_nested_delimiter="__",
        env_prefix="APP_CONFIG__",
        extra="ignore",
    )
    run: RunConfig = RunConfig()
    api: ApiConfig = ApiConfig()
    db: DatabaseConfig
    redis: RedisConfig
    details: DetailsConfig = DetailsConfig()
    bot: BotConfig
    auth: AuthConfig
    taxonomy: TaxonomyConfig = TaxonomyConfig()
    profile: ProfileConfig = ProfileConfig()
    embedding: EmbeddingConfig

    @staticmethod
    def _redis_location(url: str) -> tuple[str | None, int, str]:
        parts = urlsplit(url)
        return parts.hostname, parts.port or 6379, parts.path.lstrip("/") or "0"

    @model_validator(mode="after")
    def _refuse_insecure_production_settings(self) -> "Settings":
        if self.run.env != "prod":
            return self

        problems = []
        if self.auth.secret_key in _PLACEHOLDER_SECRET_KEYS:
            problems.append("APP_CONFIG__AUTH__SECRET_KEY is a known placeholder")
        elif len(self.auth.secret_key) < _MIN_PROD_SECRET_KEY_LENGTH:
            problems.append(f"APP_CONFIG__AUTH__SECRET_KEY is shorter than {_MIN_PROD_SECRET_KEY_LENGTH} characters")
        if self.bot.token in _PLACEHOLDER_BOT_TOKENS:
            problems.append("APP_CONFIG__BOT__TOKEN is a known placeholder")
        if self.run.reload:
            problems.append("APP_CONFIG__RUN__RELOAD must be false")
        if self.embedding.provider == "stub":
            problems.append("APP_CONFIG__EMBEDDING__PROVIDER must not be stub")
        elif self.embedding.openai_api_key is None or not self.embedding.openai_api_key.get_secret_value():
            problems.append("APP_CONFIG__EMBEDDING__OPENAI_API_KEY is required for the openai provider")
        if self._redis_location(self.embedding.broker_url) == self._redis_location(str(self.redis.url)):
            problems.append("APP_CONFIG__EMBEDDING__BROKER_URL must use a different Redis DB than APP_CONFIG__REDIS__URL")
        if problems:
            raise ValueError("Refusing to start with env=prod: " + "; ".join(problems))
        return self


settings = Settings()  # type: ignore