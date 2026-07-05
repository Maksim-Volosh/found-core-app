from app.domain.entities import NewUserEntity, UserEntity
from app.infrastructure.models import User as UserModel


class UserMapper:
    @staticmethod
    def to_entity(model: UserModel) -> UserEntity:
        return UserEntity(
            user_id=model.user_id,
            telegram_id=model.telegram_id,
            username=model.username,
            first_name=model.first_name,
            last_name=model.last_name,
            level=model.level,
            is_banned=model.is_banned,
            is_admin=model.is_admin,
            is_superadmin=model.is_superadmin,
        )

    @staticmethod
    def to_model(entity: UserEntity) -> UserModel:
        return UserModel(
            user_id=entity.user_id,
            telegram_id=entity.telegram_id,
            username=entity.username,
            first_name=entity.first_name,
            last_name=entity.last_name,
            level=entity.level,
            is_banned=entity.is_banned,
            is_admin=entity.is_admin,
            is_superadmin=entity.is_superadmin,
        )


class NewUserMapper:
    @staticmethod
    def to_entity(model: UserModel) -> NewUserEntity:
        return NewUserEntity(
            telegram_id=model.telegram_id,
            username=model.username,
            first_name=model.first_name,
            last_name=model.last_name,
        )

    @staticmethod
    def to_model(entity: NewUserEntity) -> UserModel:
        return UserModel(
            telegram_id=entity.telegram_id,
            username=entity.username,
            first_name=entity.first_name,
            last_name=entity.last_name,
            level=1,
            is_banned=False,
            is_admin=False,
            is_superadmin=False,
        )
