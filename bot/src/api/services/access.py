from src.api.api_client import APIClient


class AccessService:
    def __init__(self, api: APIClient) -> None:
        self._api = api

    async def check_main_access(self, user_id: int):
        return await self._api.get(
            f"/access/main?user_id={user_id}",
        )