import re

from app.application.services.slugify import slugify
from app.core.config import settings
from app.domain.entities import (
    CategoryEntity,
    NewTagEntity,
    NewTagScopeEntity,
    RoleEntity,
    RoleFieldEntity,
    TagEntity,
)
from app.domain.enums import TagStatus
from app.domain.exceptions import CategoryNotFoundError, RoleNotFoundError, TagTitleInvalidError
from app.domain.interfaces import ITaxonomyRepository

_MIN_TAG_TITLE_LENGTH = 2
_MAX_TAG_TITLE_LENGTH = 64
_TAG_TITLE_PATTERN = re.compile(r"^[\w\s-]+$", re.UNICODE)


class GetCategoriesUseCase:
    def __init__(self, taxonomy_repository: ITaxonomyRepository) -> None:
        self._taxonomy_repository = taxonomy_repository

    async def execute(self) -> list[CategoryEntity]:
        return await self._taxonomy_repository.get_categories()


class GetRolesByCategoryUseCase:
    def __init__(self, taxonomy_repository: ITaxonomyRepository) -> None:
        self._taxonomy_repository = taxonomy_repository

    async def execute(self, category_id: int) -> list[RoleEntity]:
        category = await self._taxonomy_repository.get_category_by_id(category_id)
        if category is None:
            raise CategoryNotFoundError()
        return await self._taxonomy_repository.get_roles_by_category(category_id)


class GetRoleFieldsByRoleUseCase:
    def __init__(self, taxonomy_repository: ITaxonomyRepository) -> None:
        self._taxonomy_repository = taxonomy_repository

    async def execute(self, role_id: int) -> list[RoleFieldEntity]:
        role = await self._taxonomy_repository.get_role_by_id(role_id)
        if role is None:
            raise RoleNotFoundError()
        return await self._taxonomy_repository.get_role_fields_by_role(role_id)


class SuggestTagsUseCase:
    def __init__(self, taxonomy_repository: ITaxonomyRepository) -> None:
        self._taxonomy_repository = taxonomy_repository

    async def execute(
        self, query: str, category_id: int, role_id: int | None, user_id: int
    ) -> list[TagEntity]:
        category = await self._taxonomy_repository.get_category_by_id(category_id)
        if category is None:
            raise CategoryNotFoundError()
        if role_id is not None:
            role = await self._taxonomy_repository.get_role_by_id(role_id)
            if role is None or role.category_id != category_id:
                raise RoleNotFoundError()
        return await self._taxonomy_repository.suggest_tags(query, category_id, role_id, user_id)


class CreateCustomTagUseCase:
    def __init__(self, taxonomy_repository: ITaxonomyRepository) -> None:
        self._taxonomy_repository = taxonomy_repository

    async def execute(self, title: str, category_id: int, role_id: int | None, user_id: int) -> TagEntity:
        title = title.strip()
        self._validate_title(title)

        category = await self._taxonomy_repository.get_category_by_id(category_id)
        if category is None:
            raise CategoryNotFoundError()
        if role_id is not None:
            role = await self._taxonomy_repository.get_role_by_id(role_id)
            if role is None or role.category_id != category_id:
                raise RoleNotFoundError()

        slug = slugify(title)
        tag = await self._taxonomy_repository.get_tag_by_slug(slug)
        if tag is None:
            tag = await self._taxonomy_repository.create_tag(
                NewTagEntity(slug=slug, title=title, status=TagStatus.PENDING, created_by_user_id=user_id)
            )

        await self._taxonomy_repository.create_tag_scope(
            NewTagScopeEntity(tag_id=tag.id, category_id=category_id, role_id=role_id)
        )
        return tag

    def _validate_title(self, title: str) -> None:
        if not (_MIN_TAG_TITLE_LENGTH <= len(title) <= _MAX_TAG_TITLE_LENGTH):
            raise TagTitleInvalidError()
        if not _TAG_TITLE_PATTERN.match(title):
            raise TagTitleInvalidError()
        lowered = title.lower()
        if any(word in lowered for word in settings.taxonomy.tag_stop_words):
            raise TagTitleInvalidError()
