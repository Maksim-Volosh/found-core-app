import pytest
from pydantic import ValidationError

from app.core.config import Settings

STRONG_SECRET = "k3J9vQ2mXw7LpR5tYb8NcA4dFg6HsZ1u"
REAL_BOT_TOKEN = "7012345678:AAH-real-looking-token-value"


def _settings(**overrides) -> Settings:
    values = {
        "db": {"url": "postgresql+asyncpg://u:p@localhost:5432/db"},
        "redis": {"url": "redis://localhost:6379/0"},
        "auth": {"secret_key": STRONG_SECRET},
        "bot": {"token": REAL_BOT_TOKEN},
        "run": {"env": "prod", "reload": False},
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_production_with_real_secrets_starts():
    settings = _settings()

    assert settings.run.env == "prod"


@pytest.mark.parametrize("secret", ["dev-only-insecure-secret-change-me", "change-me", "secret", ""])
def test_production_refuses_a_placeholder_secret_key(secret):
    with pytest.raises(ValidationError, match="SECRET_KEY is a known placeholder"):
        _settings(auth={"secret_key": secret})


def test_production_refuses_a_short_secret_key():
    with pytest.raises(ValidationError, match="shorter than 32"):
        _settings(auth={"secret_key": "x" * 31})


def test_production_accepts_a_secret_key_of_exactly_the_minimum_length():
    _settings(auth={"secret_key": "x" * 32})


@pytest.mark.parametrize("token", ["123", "key", ""])
def test_production_refuses_a_placeholder_bot_token(token):
    with pytest.raises(ValidationError, match="BOT__TOKEN is a known placeholder"):
        _settings(bot={"token": token})


def test_production_refuses_auto_reload():
    with pytest.raises(ValidationError, match="RELOAD must be false"):
        _settings(run={"env": "prod", "reload": True})


def test_production_reports_every_problem_at_once():
    with pytest.raises(ValidationError) as error:
        _settings(
            auth={"secret_key": "change-me"},
            bot={"token": "123"},
            run={"env": "prod", "reload": True},
        )

    message = str(error.value)
    assert "SECRET_KEY" in message and "BOT__TOKEN" in message and "RELOAD" in message


@pytest.mark.parametrize("env", ["dev", "test"])
def test_placeholders_are_fine_outside_production(env):
    settings = _settings(
        auth={"secret_key": "dev-only-insecure-secret-change-me"},
        bot={"token": "123"},
        run={"env": env, "reload": True},
    )

    assert settings.run.env == env


def test_unknown_environment_name_is_rejected():
    with pytest.raises(ValidationError):
        _settings(run={"env": "production"})


def test_bot_token_is_required(monkeypatch):
    monkeypatch.delenv("APP_CONFIG__BOT__TOKEN", raising=False)

    with pytest.raises(ValidationError, match="bot"):
        Settings(
            _env_file=None,
            db={"url": "postgresql+asyncpg://u:p@localhost:5432/db"},
            redis={"url": "redis://localhost:6379/0"},
            auth={"secret_key": STRONG_SECRET},
        )


def test_unprefixed_env_variable_does_not_leak_into_the_run_config(monkeypatch):
    # A generic ENV is often set by the shell; only APP_CONFIG__RUN__ENV may select the environment.
    monkeypatch.setenv("ENV", "/etc/profile")
    monkeypatch.delenv("APP_CONFIG__RUN__ENV", raising=False)

    settings = Settings(
        _env_file=None,
        db={"url": "postgresql+asyncpg://u:p@localhost:5432/db"},
        redis={"url": "redis://localhost:6379/0"},
        auth={"secret_key": STRONG_SECRET},
        bot={"token": REAL_BOT_TOKEN},
    )

    assert settings.run.env == "dev"


def test_env_template_is_not_a_settings_source():
    assert ".env.template" not in Settings.model_config["env_file"]
