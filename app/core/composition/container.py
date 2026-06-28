from sqlalchemy.ext.asyncio import AsyncSession

from app.application.use_cases import (AdminUseCase, CheckMainAccessUseCase,
                                       ClearExpiredSubscriptionsUseCase,
                                       CreatePaymentUseCase, DirectionUseCase,
                                       ProcessSuccessfulPaymentUseCase,
                                       UserAuthUseCase, UserInfoUseCase,
                                       UserUseCase)
from app.core.config import settings
from app.domain.entities.payment import PaymentProviderType
from app.infrastructure.payment_providers.stripe_provider import \
    StripePaymentProvider
from app.infrastructure.repositories import (SQLAlchemyDirectionRepository,
                                             SQLAlchemyPaymentRepository,
                                             SQLAlchemySubscriptionRepository,
                                             SQLAlchemyUserRepository)


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
    
    def direction_repo(self):
        return SQLAlchemyDirectionRepository(self.session)
    
    # ---------- payment providers ----------
    
    def _get_payment_provider(self, provider_type: PaymentProviderType):
        if provider_type == PaymentProviderType.STRIPE:
            return StripePaymentProvider(
                api_key=settings.stripe.api_key,
                success_url=settings.stripe.success_url,
                cancel_url=settings.stripe.cancel_url
            )
        raise ValueError(f"Provider {provider_type} not supported")

    # ---------- use cases ----------

    def get_user_use_case(self):
        return UserUseCase(repo=self.user_repo())
    
    def get_user_auth_use_case(self):
        return UserAuthUseCase(user_repo=self.user_repo(), subscription_repo=self.subscription_repo())
    
    def get_user_info_use_case(self):
        return UserInfoUseCase(user_repo=self.user_repo(), subscription_repo=self.subscription_repo())
    
    def get_create_payment_use_case(self, provider_type: PaymentProviderType):
        payment_provider = self._get_payment_provider(provider_type)
        return CreatePaymentUseCase(
            payment_provider=payment_provider,
            user_repo=self.user_repo(),
            payment_repo=self.payment_repo(),
            subscription_repo=self.subscription_repo(),
            default_currency=settings.payment.default_currency,
            price_matrix=settings.payment.price_matrix
        )
        
    def get_process_successful_payment_use_case(self):
        return ProcessSuccessfulPaymentUseCase(
            payment_repo=self.payment_repo(),
            subscription_repo=self.subscription_repo(),
            webhook_secret=settings.stripe.webhook_secret
        )
        
    def get_admin_use_case(self):
        return AdminUseCase(user_repo=self.user_repo())
    
    def get_clear_expired_subscriptions_use_case(self):
        return ClearExpiredSubscriptionsUseCase(subscription_repo=self.subscription_repo())
    
    def get_check_main_access_use_case(self):
        return CheckMainAccessUseCase(subscription_repo=self.subscription_repo(), user_repo=self.user_repo())
    
    def get_direction_use_case(self):
        return DirectionUseCase(repo=self.direction_repo())
