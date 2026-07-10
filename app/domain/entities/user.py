from dataclasses import dataclass
from typing import Optional

from app.domain.entities.direction import ScreeningStatus


@dataclass
class UserEntity:
    user_id: int
    telegram_id: int
    username: Optional[str]
    first_name: str
    last_name: Optional[str]
    level: int
    is_banned: bool
    is_admin: bool
    is_superadmin: bool
    screening_status: ScreeningStatus

    def calculate_subscription_price(self, price_matrix: dict[int, int]) -> int:
        """
        Calculate the subscription price based on the user's level.
        """
        return price_matrix.get(self.level, price_matrix[1])


@dataclass
class NewUserEntity:
    telegram_id: int
    username: Optional[str]
    first_name: str
    last_name: Optional[str]
