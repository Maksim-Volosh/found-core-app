from sqlalchemy import DDL, MetaData, event
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=settings.db.naming_convention)


# Only used by create_all in the integration tests, which doesn't install extensions itself.
# Migrations don't fire this event: they create pg_trgm explicitly (see the initial revision).
event.listen(Base.metadata, "before_create", DDL("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
