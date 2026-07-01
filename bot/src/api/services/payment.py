from src.api.api_client import APIClient
from src.http.errors import HTTPError


class PaymentService:
    def __init__(self, api: APIClient) -> None:
        self._api = api

    async def create(self, user_id: int, months: int, provider_type: str):
        payload = {
            "user_id": user_id,
            "months": months,
            "provider_type": provider_type
        }

        return await self._api.post(
            f"/payment/create",
            json=payload,
        )