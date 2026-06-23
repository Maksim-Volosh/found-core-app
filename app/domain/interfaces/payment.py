from abc import ABC, abstractmethod

from app.domain.entities import NewPaymentEntity, PaymentEntity
from app.domain.entities.payment import PaymentStatus


class IPaymentRepository(ABC):
    @abstractmethod
    async def create_payment(self, payment: NewPaymentEntity) -> None:
        raise NotImplementedError
    
    @abstractmethod
    async def get_pending_payment(self, user_id: int) -> PaymentEntity | None:
        raise NotImplementedError
    
    @abstractmethod
    async def update_status(self, payment_id: int, new_status: PaymentStatus) -> None:
        raise NotImplementedError
