from sqlalchemy.ext.asyncio import AsyncSession

from app.application.use_cases import (UserAuthUseCase, UserInfoUseCase,
                                       UserUseCase)
from app.application.use_cases.payment import CreatePaymentUseCase
from app.domain.entities.payment import PaymentProviderType
from app.infrastructure.payment_providers.stripe_provider import \
    StripePaymentProvider
from app.infrastructure.repositories import (SQLAlchemyPaymentRepository,
                                             SQLAlchemySubscriptionRepository,
                                             SQLAlchemyUserRepository)
from app.core.config import settings


class Container:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ---------- repositories ----------

    def user_repo(self):
        return SQLAlchemyUserRepository(self.session)

    def subscription_repo(self):
        return SQLAlchemySubscriptionRepository(self.session)
    
    def payment_repo(self):
        return SQLAlchemyPaymentRepository(self.session)
    
    # ---------- payment providers ----------
    
    def _get_payment_provider(self, provider_type: PaymentProviderType):
        if provider_type == PaymentProviderType.STRIPE:
            return StripePaymentProvider()
        raise ValueError(f"Provider {provider_type} not supported")

    # ---------- use cases ----------

    def user_use_case(self):
        return UserUseCase(repo=self.user_repo())
    
    def user_auth_use_case(self):
        return UserAuthUseCase(user_repo=self.user_repo(), subscription_repo=self.subscription_repo())
    
    def user_info_use_case(self):
        return UserInfoUseCase(user_repo=self.user_repo(), subscription_repo=self.subscription_repo())
    
    def create_payment_use_case(self, provider_type: PaymentProviderType):
        payment_provider = self._get_payment_provider(provider_type)
        return CreatePaymentUseCase(
            payment_provider=payment_provider,
            user_repo=self.user_repo(),
            payment_repo=self.payment_repo(),
            default_currency=settings.payment.default_currency,
            price_matrix=settings.payment.price_matrix
        )