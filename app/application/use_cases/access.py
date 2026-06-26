from app.domain.interfaces import (ISubscriptionRepository, IUserRepository)

class CheckMainAccessUseCase:
    def __init__(self, subscription_repo: ISubscriptionRepository, user_repo: IUserRepository):
        self.subscription_repo = subscription_repo
        self.user_repo = user_repo

    async def execute(self, user_id: int) -> bool:
        subscription = await self.subscription_repo.get_subscription(user_id)
        
        if not subscription:
            return False
            
        if subscription.status == "ACTIVE":
            return True
            
        return False