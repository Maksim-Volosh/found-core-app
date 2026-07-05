from app.domain.entities.direction import DirectionEntity, UserDirectionAccessEntity
from app.infrastructure.models import UserDirectionAccess as UserDirectionAccessModel
from app.infrastructure.models import Direction as DirectionModel


class DirectionMapper:
    @staticmethod
    def to_model(entity: DirectionEntity) -> DirectionModel:
        return DirectionModel(
            telegram_chat_id=entity.telegram_chat_id,
            name=entity.name,
            owner_username=entity.owner_username,
            requires_screening=entity.requires_screening,
        )

    @staticmethod
    def from_model(model: DirectionModel) -> DirectionEntity:
        return DirectionEntity(
            telegram_chat_id=model.telegram_chat_id,
            name=model.name,
            owner_username=model.owner_username,
            requires_screening=model.requires_screening,
        )


class UserDirectionAccessMapper:
    @staticmethod
    def to_model(entity: UserDirectionAccessEntity) -> UserDirectionAccessModel:
        return UserDirectionAccessModel(
            user_id=entity.user_id,
            telegram_chat_id=entity.telegram_chat_id,
            screening_status=entity.screening_status,
        )

    @staticmethod
    def from_model(model: UserDirectionAccessModel) -> UserDirectionAccessEntity:
        return UserDirectionAccessEntity(
            user_id=model.user_id,
            telegram_chat_id=model.telegram_chat_id,
            screening_status=model.screening_status,
        )
