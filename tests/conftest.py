"""Shared fixtures for the auth-telegram test suite.

`.env.test` is loaded *before* any `app.*` import, since `app.core.config.settings`
and `app.infrastructure.helpers.db_helper` are module-level singletons built at
import time from whatever is in `os.environ` right then.
"""

from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env.test", override=True)

from collections.abc import AsyncIterator
from urllib.parse import unquote, urlsplit

import asyncpg
import httpx
import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from httpx import ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.composition.container import Container
from app.core.config import settings
from app.infrastructure.helpers import db_helper
from app.infrastructure.models import Base
from app.main import main_app


def _parse_db_url(url: str) -> dict:
    parts = urlsplit(url)
    return {
        "user": unquote(parts.username or ""),
        "password": unquote(parts.password or ""),
        "host": parts.hostname,
        "port": parts.port or 5432,
        "database": (parts.path or "/").lstrip("/"),
    }


@pytest_asyncio.fixture(autouse=True)
async def _test_database() -> AsyncIterator[None]:
    """Runs before/after every test, entirely within that test's own event
    loop. pytest-asyncio gives each test function a fresh loop by default,
    and asyncpg connections are bound to the loop they're created on -- a
    session-scoped setup fixture (opening connections once, up front) would
    leave the shared `db_helper.engine` pool bound to a loop that later tests
    don't share, causing "attached to a different loop" errors. Disposing
    the engine at the end of every test avoids that: the next test's first
    use of `db_helper.engine` reconnects fresh, in its own loop.
    """
    params = _parse_db_url(str(settings.db.url))

    conn = await asyncpg.connect(
        user=params["user"],
        password=params["password"],
        host=params["host"],
        port=params["port"],
        database="postgres",
    )
    try:
        await conn.execute(f'CREATE DATABASE "{params["database"]}"')
    except asyncpg.DuplicateDatabaseError:
        pass
    finally:
        await conn.close()

    async with db_helper.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with db_helper.engine.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE users RESTART IDENTITY CASCADE"))
    await db_helper.engine.dispose()


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async with db_helper.session_factory() as s:
        yield s


@pytest.fixture
def container(session: AsyncSession) -> Container:
    return Container(session=session)


@pytest_asyncio.fixture
async def async_client() -> AsyncIterator[httpx.AsyncClient]:
    """Drives the real app through its real ASGI lifespan (table creation on
    startup, engine disposal on shutdown) against the test database."""
    async with LifespanManager(main_app):
        transport = ASGITransport(app=main_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
