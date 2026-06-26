from src.api.api_client import APIClient
from src.http.errors import HTTPError


class UserService:
    def __init__(self, api: APIClient) -> None:
        self._api = api

    async def get_uset_info(self, user_id: int):
        return await self._api.get(
            f"/user/{user_id}"
        )