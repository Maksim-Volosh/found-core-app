from app.api.v1.mappers.user import map_user_entity_to_user_public_schema
from app.api.v1.schemas import TelegramAuthResponse
from app.domain.entities import TelegramAuthResult


def map_telegram_auth_result_to_telegram_auth_response(
    result: TelegramAuthResult,
) -> TelegramAuthResponse:
    return TelegramAuthResponse(
        access_token=result.access_token,
        is_new_user=result.is_new_user,
        user=map_user_entity_to_user_public_schema(result.user),
        profiles=[],
    )
