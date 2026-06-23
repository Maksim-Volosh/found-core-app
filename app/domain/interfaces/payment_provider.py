from abc import ABC, abstractmethod

from app.domain.entities import PaymentSessionEntity
from app.domain.entities.payment import PaymentProviderType


class IPaymentProvider(ABC):
    @property
    @abstractmethod
    def provider(self) -> PaymentProviderType:
        pass
    
    @abstractmethod
    async def create_checkout_session(self, user_id: int, price_in_cents: int, currency: str) -> PaymentSessionEntity:
        raise NotImplementedError
    