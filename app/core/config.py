from pydantic import BaseModel, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class RunConfig(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True


class DetailsConfig(BaseModel):
    title: str = "FastAPI App"
    description: str = "API"


class ApiConfig(BaseModel):
    prefix: str = "/api"


class SecurityConfig(BaseModel):
    bot_api_key: str


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


class CacheConfig(BaseSettings):
    url: str
    

class StripeConfig(BaseSettings):
    api_key: str
    webhook_secret: str
    success_url: str
    cancel_url: str
    

class PaymentConfig(BaseSettings):
    default_currency: str = "EUR"
    price_matrix: dict[int, int] = {
        1: 500,
        2: 500,
        3: 500,
        4: 300,
        5: 300,
        6: 300,
        7: 300,
        8: 0,
        9: 0,
        10: 0,
    }
    
    
class TelegramConfig(BaseSettings):
    bot_token: str
    main_chat_id: int


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env.template", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_nested_delimiter="__",
        env_prefix="APP_CONFIG__",
    )
    run: RunConfig = RunConfig()
    security: SecurityConfig
    stripe: StripeConfig
    payment: PaymentConfig = PaymentConfig()
    telegram: TelegramConfig
    api: ApiConfig = ApiConfig()
    db: DatabaseConfig
    cache: CacheConfig
    details: DetailsConfig = DetailsConfig()


settings = Settings()  # type: ignore