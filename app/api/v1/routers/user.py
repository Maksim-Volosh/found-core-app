from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.mappers.user import map_telegram_auth_result_to_telegram_auth_response
from app.api.v1.schemas import TelegramAuthRequest, TelegramAuthResponse
from app.core.composition.container import Container
from app.core.composition.di import get_container
from app.domain.exceptions import (
    InitDataExpiredError,
    InitDataMalformedError,
    InitDataSignatureInvalidError,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/telegram")
async def auth_via_telegram(
    payload: TelegramAuthRequest,
    container: Container = Depends(get_container),
) -> TelegramAuthResponse:
    try:
        result = await container.auth_use_case().execute(payload.init_data)
    except InitDataMalformedError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except (InitDataSignatureInvalidError, InitDataExpiredError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return map_telegram_auth_result_to_telegram_auth_response(result)
