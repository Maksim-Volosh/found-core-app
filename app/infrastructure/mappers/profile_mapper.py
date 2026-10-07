from app.domain.entities import ProfileEntity, TagEntity
from app.infrastructure.models import ProfileModel


def map_profile_model_to_profile_entity(model: ProfileModel, tags: list[TagEntity]) -> ProfileEntity:
    return ProfileEntity(
        id=model.id,
        user_id=model.user_id,
        category_id=model.category_id,
        role_id=model.role_id,
        country_code=model.country_code,
        timezone=model.timezone,
        bio=model.bio,
        goals_description=model.goals_description,
        extra_attributes=model.extra_attributes,
        status=model.status,
        created_at=model.created_at,
        updated_at=model.updated_at,
        tags=tags,
    )
