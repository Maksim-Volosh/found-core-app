from src.api.api_client import APIClient
from src.http.errors import HTTPError


class AdminService:
    def __init__(self, api: APIClient) -> None:
        self._api = api

    async def get_all_users(self):
        return await self._api.get(
            f"/admin/user",
        )

    async def get_user_by_username(self, username: str):
        return await self._api.get(
            f"/admin/user/{username}",
        )

    async def ban_user(self, user_id: int, decision: bool):
        return await self._api.patch(
            f"/admin/user/{user_id}/ban?decision={decision}",
        )

    async def change_user_level(self, user_id: int, level: int):
        return await self._api.patch(
            f"/admin/user/{user_id}/level?level={level}",
        )

    async def change_user_screening_status(self, user_id: int, status: str):
        return await self._api.patch(
            f"/admin/user/{user_id}/screening_status?status={status}",
        )

    async def update_user_direction_access(
        self, user_id: int, telegram_chat_id: int, access: str
    ):
        return await self._api.patch(
            f"/admin/direction/access?user_id={user_id}&telegram_chat_id={telegram_chat_id}",
            json={"screening_status": access},
        )

    async def give_subscription(self, user_id: int, months: int):
        return await self._api.post(
            f"/admin/user/{user_id}/subscription/give?months={months}",
        )

    async def toggle_admin(self, user_id: int, decision: bool):
        return await self._api.patch(
            f"/admin/user/{user_id}/admin?decision={decision}",
        )
