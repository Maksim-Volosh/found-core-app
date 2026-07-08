from app.domain.interfaces import ISubscriptionRepository, IUserRepository


class CheckMainAccessUseCase:
    def __init__(
        self,
        subscription_repo: ISubscriptionRepository,
        user_repo: IUserRepository,
        price_matrix: dict[int, int],
    ):
        self.subscription_repo = subscription_repo
        self.user_repo = user_repo
        self.price_matrix = price_matrix

    async def execute(self, user_id: int) -> bool:
        subscription = await self.subscription_repo.get_subscription(user_id)
        user = await self.user_repo.get_by_user_id(user_id)

        if user is None:
            return False
        if user.is_banned:
            return False
        if user.is_admin:
            return True
        price_in_cents = user.calculate_subscription_price(self.price_matrix)
        if price_in_cents == 0:
            return True

        if not subscription:
            return False

        if subscription.status == "ACTIVE":
            return True

        return False
