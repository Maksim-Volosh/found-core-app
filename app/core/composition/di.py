from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.composition.container import Container
from app.infrastructure.helpers.db import db_helper


async def get_container(
    session: AsyncSession = Depends(db_helper.session_getter),
) -> Container:
    return Container(session=session)
