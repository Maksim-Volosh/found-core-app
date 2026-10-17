from sqlalchemy import DDL, MetaData, event
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=settings.db.naming_convention)


# Only used by create_all in the integration tests, which doesn't install extensions itself.
# Migrations don't fire these events: they create the extensions explicitly (see the revisions).
event.listen(Base.metadata, "before_create", DDL("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
event.listen(Base.metadata, "before_create", DDL("CREATE EXTENSION IF NOT EXISTS vector"))
