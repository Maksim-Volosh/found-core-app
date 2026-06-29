from src.api.api_client import APIClient
from src.http.errors import HTTPError


class AdminService:
    def __init__(self, api: APIClient) -> None:
        self._api = api

    async def get_all_users(self):
        return await self._api.get(
            f"/admin/user",
        )
        
    async def ban_user(self, user_id: int, decision: bool):
        return await self._api.patch(
            f"/admin/user/{user_id}/ban?decision={decision}",
        )
        
    async def change_user_level(self, user_id: int, level: int):
        return await self._api.patch(
            f"/admin/user/{user_id}/level?level={level}",
        )