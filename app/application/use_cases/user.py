from datetime import datetime, timezone

from app.application.services.jwt_service import JWTService
from app.application.services.telegram_init_data import TelegramInitDataValidator
from app.domain.entities import NewUserEntity, TelegramAuthResult
from app.domain.interfaces import IUserRepository


class AuthenticateTelegramUserUseCase:
    def __init__(
        self,
        user_repository: IUserRepository,
        init_data_validator: TelegramInitDataValidator,
        jwt_service: JWTService,
    ) -> None:
        self._user_repository = user_repository
        self._init_data_validator = init_data_validator
        self._jwt_service = jwt_service

    async def execute(self, init_data_raw: str) -> TelegramAuthResult:
        parsed = self._init_data_validator.validate(init_data_raw)
        tg_user = parsed.user
        now = datetime.now(timezone.utc)

        existing = await self._user_repository.get_by_telegram_id(tg_user.id)
        if existing is not None:
            existing.first_name = tg_user.first_name
            existing.last_name = tg_user.last_name
            existing.username = tg_user.username
            existing.photo_url = tg_user.photo_url
            existing.language_code = tg_user.language_code
            existing.last_active_at = now
            user = await self._user_repository.update(existing)
            is_new_user = False
        else:
            user = await self._user_repository.create(
                NewUserEntity(
                    telegram_id=tg_user.id,
                    first_name=tg_user.first_name,
                    created_at=now,
                    last_active_at=now,
                    last_name=tg_user.last_name,
                    username=tg_user.username,
                    photo_url=tg_user.photo_url,
                    language_code=tg_user.language_code,
                )
            )
            is_new_user = True

        token = self._jwt_service.create_access_token(
            user_id=user.id,
            telegram_id=user.telegram_id,
            token_version=user.token_version,
            is_admin=user.is_admin,
        )
        return TelegramAuthResult(user=user, access_token=token, is_new_user=is_new_user)
