from sqlalchemy import DDL, MetaData, event
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=settings.db.naming_convention)


# pg_trgm is required by the GIN tag-search index; create_all doesn't install extensions itself.
event.listen(Base.metadata, "before_create", DDL("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
