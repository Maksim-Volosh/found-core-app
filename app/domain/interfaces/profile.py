from abc import ABC, abstractmethod

from app.domain.entities import NewProfileEntity, ProfileEntity
from app.domain.enums import ProfileStatus


class IProfileRepository(ABC):
    @abstractmethod
    async def get_by_id(self, profile_id: int) -> ProfileEntity | None: ...

    @abstractmethod
    async def get_by_user_category_role(
        self, user_id: int, category_id: int, role_id: int
    ) -> ProfileEntity | None: ...

    @abstractmethod
    async def list_by_user_id(self, user_id: int) -> list[ProfileEntity]:
        """Ordered by created_at, id."""

    @abstractmethod
    async def get_newest_active_by_user_id(self, user_id: int) -> ProfileEntity | None:
        """Newest by created_at DESC, id DESC among the user's profiles with status active."""

    @abstractmethod
    async def create(self, profile: NewProfileEntity) -> ProfileEntity | None:
        """Inserts the profile together with its tag links.

        Returns None if a profile for the same (user, category, role) already exists.
        """

    @abstractmethod
    async def update(self, profile: ProfileEntity, tag_ids: list[int]) -> ProfileEntity:
        """Writes the editable content and replaces the tag links. Never changes status, category or role."""

    @abstractmethod
    async def set_status(self, profile_id: int, status: ProfileStatus) -> None: ...

    @abstractmethod
    async def delete(self, profile_id: int) -> None: ...
