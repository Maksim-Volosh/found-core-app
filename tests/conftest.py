"""Shared test setup.

`.env.test` is loaded *before* any `app.*` import, since `app.core.config.settings`
and `app.infrastructure.helpers.db_helper` are module-level singletons built at
import time from whatever is in `os.environ` right then.

Database/Redis fixtures live in `tests/integration/conftest.py`, so unit tests
never need Postgres or Redis.
"""

from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env.test", override=True)
