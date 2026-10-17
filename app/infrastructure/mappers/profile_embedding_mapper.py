from app.domain.entities import ProfileEmbeddingEntity
from app.infrastructure.models import ProfileEmbeddingModel


def map_profile_embedding_model_to_profile_embedding_entity(
    model: ProfileEmbeddingModel,
) -> ProfileEmbeddingEntity:
    return ProfileEmbeddingEntity(
        profile_id=model.profile_id,
        input_hash=model.input_hash,
        model=model.model,
        status=model.status,
        source_updated_at=model.source_updated_at,
        updated_at=model.updated_at,
    )
