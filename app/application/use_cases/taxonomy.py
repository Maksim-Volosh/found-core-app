from dataclasses import asdict

from app.application.services.slugify import slugify
from app.domain.entities import (
    CategoryEntity,
    NewTagEntity,
    NewTagScopeEntity,
    RoleEntity,
    RoleFieldEntity,
    TagEntity,
)
from app.domain.enums import RoleFieldType, TagStatus
from app.domain.exceptions import CategoryNotFoundError, RoleNotFoundError
from app.domain.interfaces import ICacheRepository, ITaxonomyRepository
from app.domain.services import TagTitleValidator

_CATEGORIES_CACHE_KEY = "taxonomy:categories"
_ROLES_CACHE_KEY_TEMPLATE = "taxonomy:roles:{category_id}"
_ROLE_FIELDS_CACHE_KEY_TEMPLATE = "taxonomy:role_fields:{role_id}"


class GetCategoriesUseCase:
    def __init__(
        self,
        taxonomy_repository: ITaxonomyRepository,
        cache_repository: ICacheRepository,
        cache_ttl_seconds: int,
    ) -> None:
        self._taxonomy_repository = taxonomy_repository
        self._cache_repository = cache_repository
        self._cache_ttl_seconds = cache_ttl_seconds

    async def execute(self) -> list[CategoryEntity]:
        cached = await self._cache_repository.get(_CATEGORIES_CACHE_KEY)
        if cached is not None:
            return [CategoryEntity(**item) for item in cached]

        categories = await self._taxonomy_repository.get_categories()
        await self._cache_repository.set(
            _CATEGORIES_CACHE_KEY, [asdict(c) for c in categories], self._cache_ttl_seconds
        )
        return categories


class GetRolesByCategoryUseCase:
    def __init__(
        self,
        taxonomy_repository: ITaxonomyRepository,
        cache_repository: ICacheRepository,
        cache_ttl_seconds: int,
    ) -> None:
        self._taxonomy_repository = taxonomy_repository
        self._cache_repository = cache_repository
        self._cache_ttl_seconds = cache_ttl_seconds

    async def execute(self, category_id: int) -> list[RoleEntity]:
        category = await self._taxonomy_repository.get_category_by_id(category_id)
        if category is None:
            raise CategoryNotFoundError()

        key = _ROLES_CACHE_KEY_TEMPLATE.format(category_id=category_id)
        cached = await self._cache_repository.get(key)
        if cached is not None:
            return [RoleEntity(**item) for item in cached]

        roles = await self._taxonomy_repository.get_roles_by_category(category_id)
        await self._cache_repository.set(key, [asdict(r) for r in roles], self._cache_ttl_seconds)
        return roles


class GetRoleFieldsByRoleUseCase:
    def __init__(
        self,
        taxonomy_repository: ITaxonomyRepository,
        cache_repository: ICacheRepository,
        cache_ttl_seconds: int,
    ) -> None:
        self._taxonomy_repository = taxonomy_repository
        self._cache_repository = cache_repository
        self._cache_ttl_seconds = cache_ttl_seconds

    async def execute(self, role_id: int) -> list[RoleFieldEntity]:
        role = await self._taxonomy_repository.get_role_by_id(role_id)
        if role is None:
            raise RoleNotFoundError()

        key = _ROLE_FIELDS_CACHE_KEY_TEMPLATE.format(role_id=role_id)
        cached = await self._cache_repository.get(key)
        if cached is not None:
            return [
                RoleFieldEntity(**{**item, "field_type": RoleFieldType(item["field_type"])}) for item in cached
            ]

        fields = await self._taxonomy_repository.get_role_fields_by_role(role_id)
        await self._cache_repository.set(key, [asdict(f) for f in fields], self._cache_ttl_seconds)
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
