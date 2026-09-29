from abc import ABC, abstractmethod

from app.domain.entities import CategoryEntity, RoleEntity, RoleFieldEntity


class ITaxonomyCacheRepository(ABC):
    @abstractmethod
    async def get_categories(self) -> list[CategoryEntity] | None: ...

    @abstractmethod
    async def set_categories(self, categories: list[CategoryEntity]) -> None: ...

    @abstractmethod
    async def get_roles_by_category(self, category_id: int) -> list[RoleEntity] | None: ...

    @abstractmethod
    async def set_roles_by_category(self, category_id: int, roles: list[RoleEntity]) -> None: ...

    @abstractmethod
    async def get_role_fields_by_role(self, role_id: int) -> list[RoleFieldEntity] | None: ...

    @abstractmethod
    async def set_role_fields_by_role(self, role_id: int, fields: list[RoleFieldEntity]) -> None: ...
