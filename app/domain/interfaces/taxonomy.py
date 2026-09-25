from abc import ABC, abstractmethod

from app.domain.entities import (
    CategoryEntity,
    NewTagEntity,
    NewTagScopeEntity,
    RoleEntity,
    RoleFieldEntity,
    TagEntity,
    TagScopeEntity,
)


class ITaxonomyRepository(ABC):
    @abstractmethod
    async def get_categories(self) -> list[CategoryEntity]: ...

    @abstractmethod
    async def get_category_by_id(self, category_id: int) -> CategoryEntity | None: ...

    @abstractmethod
    async def get_roles_by_category(self, category_id: int) -> list[RoleEntity]: ...

    @abstractmethod
    async def get_role_by_id(self, role_id: int) -> RoleEntity | None: ...

    @abstractmethod
    async def get_role_fields_by_role(self, role_id: int) -> list[RoleFieldEntity]: ...

    @abstractmethod
    async def suggest_tags(
        self, query: str, category_id: int, role_id: int | None, user_id: int
    ) -> list[TagEntity]: ...

    @abstractmethod
    async def get_tag_by_slug(self, slug: str) -> TagEntity | None: ...

    @abstractmethod
    async def create_tag(self, tag: NewTagEntity) -> TagEntity: ...

    @abstractmethod
    async def create_tag_scope(self, scope: NewTagScopeEntity) -> TagScopeEntity: ...
