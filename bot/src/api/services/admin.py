from src.api.api_client import APIClient
from src.http.errors import HTTPError


class AdminService:
    def __init__(self, api: APIClient) -> None:
        self._api = api

    async def get_all_users(self):
        return await self._api.get(
            f"/admin/user",
        )