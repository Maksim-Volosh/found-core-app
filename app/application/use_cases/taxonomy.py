from app.application.services.slugify import slugify
from app.domain.entities import (
    CategoryEntity,
    NewTagEntity,
    NewTagScopeEntity,
    RoleEntity,
    RoleFieldEntity,
    TagEntity,
)
from app.domain.enums import TagStatus
from app.domain.exceptions import CategoryNotFoundError, RoleNotFoundError
from app.domain.interfaces import ITaxonomyCacheRepository, ITaxonomyRepository
from app.domain.services import TagTitleValidator


class GetCategoriesUseCase:
    def __init__(
        self,
        taxonomy_repository: ITaxonomyRepository,
        taxonomy_cache_repository: ITaxonomyCacheRepository,
    ) -> None:
        self._taxonomy_repository = taxonomy_repository
        self._taxonomy_cache_repository = taxonomy_cache_repository

    async def execute(self) -> list[CategoryEntity]:
        cached = await self._taxonomy_cache_repository.get_categories()
        if cached is not None:
            return cached

        categories = await self._taxonomy_repository.get_categories()
        await self._taxonomy_cache_repository.set_categories(categories)
        return categories


class GetRolesByCategoryUseCase:
    def __init__(
        self,
        taxonomy_repository: ITaxonomyRepository,
        taxonomy_cache_repository: ITaxonomyCacheRepository,
    ) -> None:
        self._taxonomy_repository = taxonomy_repository
        self._taxonomy_cache_repository = taxonomy_cache_repository

    async def execute(self, category_id: int) -> list[RoleEntity]:
        category = await self._taxonomy_repository.get_category_by_id(category_id)
        if category is None:
            raise CategoryNotFoundError()

        cached = await self._taxonomy_cache_repository.get_roles_by_category(category_id)
        if cached is not None:
            return cached

        roles = await self._taxonomy_repository.get_roles_by_category(category_id)
        await self._taxonomy_cache_repository.set_roles_by_category(category_id, roles)
        return roles


class GetRoleFieldsByRoleUseCase:
    def __init__(
        self,
        taxonomy_repository: ITaxonomyRepository,
        taxonomy_cache_repository: ITaxonomyCacheRepository,
    ) -> None:
        self._taxonomy_repository = taxonomy_repository
        self._taxonomy_cache_repository = taxonomy_cache_repository

    async def execute(self, role_id: int) -> list[RoleFieldEntity]:
        role = await self._taxonomy_repository.get_role_by_id(role_id)
        if role is None:
            raise RoleNotFoundError()

        cached = await self._taxonomy_cache_repository.get_role_fields_by_role(role_id)
        if cached is not None:
            return cached

        fields = await self._taxonomy_repository.get_role_fields_by_role(role_id)
        await self._taxonomy_cache_repository.set_role_fields_by_role(role_id, fields)
        return fields


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
    def __init__(
        self,
        taxonomy_repository: ITaxonomyRepository,
        tag_title_validator: TagTitleValidator,
    ) -> None:
        self._taxonomy_repository = taxonomy_repository
        self._tag_title_validator = tag_title_validator

    async def execute(self, title: str, category_id: int, role_id: int | None, user_id: int) -> TagEntity:
        title = title.strip()
        self._tag_title_validator.validate(title)

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
