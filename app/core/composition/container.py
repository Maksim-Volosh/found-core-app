from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.payment import ProcessSuccessfulPaymentService
from app.application.use_cases import (AdminSubscriptionUseCase, AdminUseCase,
                                       CheckMainAccessUseCase,
                                       ClearExpiredSubscriptionsUseCase,
                                       CreateDirectionUseCase,
                                       CreatePaymentUseCase, DirectionUseCase,
                                       ProcessCryptoPaymentUseCase,
                                       ProcessStripePaymentUseCase,
                                       SendSubscriptionRemindersUseCase,
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
from app.infrastructure.repositories.telegram_bot import TelegramBotService


class Container:
    def __init__(self, session: AsyncSession):
        self.session = session
        
    # ---------- services ----------
    
    def get_bot_service(self):
        return TelegramBotService()
    
    def get_successful_payment_service(self):
        return ProcessSuccessfulPaymentService(
            payment_repo=self.payment_repo(),
            subscription_repo=self.subscription_repo(),
        )

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
        elif provider_type == PaymentProviderType.CRYPTO:
            from app.infrastructure.payment_providers.crypto_bot_provider import \
                CryptoBotPaymentProvider
            return CryptoBotPaymentProvider(
                api_key=settings.crypto_bot.api_key,
                is_testnet=settings.crypto_bot.is_testnet
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
        
    def get_stripe_process_successful_payment_use_case(self):
        return ProcessStripePaymentUseCase(
            payment_service=self.get_successful_payment_service(),
            webhook_secret=settings.stripe.webhook_secret
        )
        
    def get_crypto_process_successful_payment_use_case(self):
        return ProcessCryptoPaymentUseCase(
            payment_service=self.get_successful_payment_service(),
            crypto_bot_token=settings.crypto_bot.api_key
        )
        
    def get_admin_use_case(self):
        return AdminUseCase(user_repo=self.user_repo())
    
    def get_admin_subscription_use_case(self):
        return AdminSubscriptionUseCase(user_repo=self.user_repo(), subscription_repo=self.subscription_repo())
    
    def get_clear_expired_subscriptions_use_case(self):
        return ClearExpiredSubscriptionsUseCase(subscription_repo=self.subscription_repo(), direction_repo=self.direction_repo(), user_repo=self.user_repo(), bot_service=self.get_bot_service())
    
    def get_send_subscription_reminders_use_case(self):
        return SendSubscriptionRemindersUseCase(subscription_repo=self.subscription_repo(), user_repo=self.user_repo(), bot_service=self.get_bot_service())
    
    def get_check_main_access_use_case(self):
        return CheckMainAccessUseCase(subscription_repo=self.subscription_repo(), user_repo=self.user_repo(), price_matrix=settings.payment.price_matrix)
    
    def get_direction_use_case(self):
        return DirectionUseCase(repo=self.direction_repo())

    def get_create_direction_use_case(self):
        return CreateDirectionUseCase(direction_repo=self.direction_repo(), user_repo=self.user_repo())