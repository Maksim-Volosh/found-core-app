from typing import Literal

from pydantic import BaseModel, PostgresDsn, RedisDsn, model_validator
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
        if problems:
            raise ValueError("Refusing to start with env=prod: " + "; ".join(problems))
        return self


settings = Settings()  # type: ignore