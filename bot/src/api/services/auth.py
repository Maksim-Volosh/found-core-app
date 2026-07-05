from src.api.api_client import APIClient
from src.http.errors import HTTPError


class AuthService:
    def __init__(self, api: APIClient) -> None:
        self._api = api

    async def auth(self, data: dict, telegram_id: int):
        payload = {
            "telegram_id": telegram_id,
            "username": data["username"],
            "first_name": data["first_name"],
            "last_name": data["last_name"],
        }

        return await self._api.post(
            f"/user/auth",
            json=payload,
            expected_status=200,
        )
