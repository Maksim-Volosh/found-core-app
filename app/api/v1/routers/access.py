from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from app.core.composition.container import Container
from app.core.composition.di import get_container
from app.infrastructure.helpers.db import db_helper
from app.api.v1.schemas.access import AccessResponse

router = APIRouter(prefix="/access", tags=["Access"])


@router.get("/main")
async def check_main_access(
    user_id: int,
    container: Container = Depends(get_container),
) -> AccessResponse:
    use_case = container.get_check_main_access_use_case()
    
    is_allowed = await use_case.execute(user_id=user_id)
    
    return AccessResponse(allowed=is_allowed)