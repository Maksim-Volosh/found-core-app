from app.api.v1.mappers.taxonomy import map_tag_entity_to_tag_schema
from app.api.v1.schemas import (
    CountrySchema,
    ProfileFormConfigSchema,
    ProfileSchema,
    ProfileUpdateRequest,
    TagLimitsSchema,
    TextLimitsSchema,
    TimezoneSchema,
)
from app.core.config import ProfileConfig
from app.domain.entities import CountryEntity, ProfileEntity, ProfileFormEntity


def map_profile_entity_to_profile_schema(entity: ProfileEntity, active_profile_id: int | None) -> ProfileSchema:
    return ProfileSchema(
        id=entity.id,
        category_id=entity.category_id,
        role_id=entity.role_id,
        country_code=entity.country_code,
        timezone=entity.timezone,
        bio=entity.bio,
        goals_description=entity.goals_description,
        extra_attributes=entity.extra_attributes,
        status=entity.status,
        is_active=entity.id == active_profile_id,
        tags=[map_tag_entity_to_tag_schema(t) for t in entity.tags],
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def map_profile_update_request_to_profile_form_entity(payload: ProfileUpdateRequest) -> ProfileFormEntity:
    return ProfileFormEntity(
        country_code=payload.country_code,
        timezone=payload.timezone,
        bio=payload.bio,
        goals_description=payload.goals_description,
        tag_ids=payload.tag_ids,
    )


def map_profile_form_config_to_profile_form_config_schema(
    config: ProfileConfig, countries: list[CountryEntity]
) -> ProfileFormConfigSchema:
    return ProfileFormConfigSchema(
        bio=TextLimitsSchema(min_length=config.bio_min_length, max_length=config.bio_max_length),
        goals=TextLimitsSchema(min_length=config.goals_min_length, max_length=config.goals_max_length),
        tags=TagLimitsSchema(min_count=config.tags_min_count, max_count=config.tags_max_count),
        countries=[
            CountrySchema(
                code=country.code,
                name=country.name,
                timezones=[
                    TimezoneSchema(id=tz.id, label=tz.label, utc_offset=tz.utc_offset)
                    for tz in country.timezones
                ],
            )
            for country in countries
        ],
    )
