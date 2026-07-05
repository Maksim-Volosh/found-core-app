from src.api.api_client import APIClient
from src.http.errors import HTTPError


class DirectionService:
    def __init__(self, api: APIClient) -> None:
        self._api = api

    async def get_directions(self):
        return await self._api.get(
            f"/direction",
        )

    async def get_direction(self, telegram_chat_id: int):
        return await self._api.get(
            f"/direction/{telegram_chat_id}",
        )

    async def update_direction(
        self,
        name: str,
        owner_username: str,
        requires_screening: bool,
        telegram_chat_id: int,
    ):
        payload = {
            "name": name,
            "owner_username": owner_username,
            "requires_screening": requires_screening,
        }

        return await self._api.patch(
            f"/admin/direction/{telegram_chat_id}",
            json=payload,
        )

    async def create_direction(
        self,
        telegram_chat_id: int,
        name: str,
        owner_username: str,
        requires_screening: bool,
    ):
        payload = {
            "telegram_chat_id": telegram_chat_id,
            "name": name,
            "owner_username": owner_username,
            "requires_screening": requires_screening,
        }

        return await self._api.post(
            f"/admin/direction",
            json=payload,
        )

    async def get_direction_access(self, user_id: int, telegram_chat_id: int):
        return await self._api.get(
            f"/direction/{user_id}/access?telegram_chat_id={telegram_chat_id}",
        )

    async def create_direction_access(self, user_id: int, telegram_chat_id: int):
        payload = {"user_id": user_id, "telegram_chat_id": telegram_chat_id}
        return await self._api.post(
            f"/direction/access",
            json=payload,
        )
