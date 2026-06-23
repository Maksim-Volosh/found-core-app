from abc import ABC, abstractmethod

from app.domain.entities import NewPaymentEntity


class IPaymentRepository(ABC):
    @abstractmethod
    async def create_payment(self, payment: NewPaymentEntity) -> None:
        raise NotImplementedError
