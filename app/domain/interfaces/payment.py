from abc import ABC, abstractmethod

from app.domain.entities import NewPaymentEntity, PaymentEntity
from app.domain.entities.payment import PaymentStatus


class IPaymentRepository(ABC):
    @abstractmethod
    async def commit(self) -> None:
        raise NotImplementedError
    
    @abstractmethod
    async def create_payment(self, payment: NewPaymentEntity) -> None:
        raise NotImplementedError
    
    @abstractmethod
    async def get_pending_payment(self, user_id: int) -> PaymentEntity | None:
        raise NotImplementedError
    
    @abstractmethod
    async def get_by_provider_payment_id(self, provider_payment_id: str) -> PaymentEntity | None:
        raise NotImplementedError
    
    @abstractmethod
    async def update_status(self, payment_id: int, new_status: PaymentStatus) -> None:
        raise NotImplementedError
