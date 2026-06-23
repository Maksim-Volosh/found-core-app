from abc import ABC, abstractmethod

from app.domain.entities import PaymentSessionEntity


class IPaymentProvider(ABC):
    @abstractmethod
    async def create_checkout_session(self, user_id: int, price_in_cents: int) -> PaymentSessionEntity:
        raise NotImplementedError
    