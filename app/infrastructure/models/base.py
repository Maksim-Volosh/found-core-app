from sqlalchemy import DDL, MetaData, event
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=settings.db.naming_convention)


# pg_trgm нужен GIN-индексу поиска по тегам; create_all сам расширения не ставит.
event.listen(Base.metadata, "before_create", DDL("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
