from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import NewPaymentEntity
from app.domain.entities.payment import PaymentEntity, PaymentStatus
from app.domain.interfaces import IPaymentRepository
from app.infrastructure.mappers.payment import NewPaymentMapper, PaymentMapper
from app.infrastructure.models.payment import Payment


class SQLAlchemyPaymentRepository(IPaymentRepository):
    def __init__(self, session):
        self.session: AsyncSession = session
        
    def commit(self):
        return self.session.commit()
    
    async def create_payment(self, payment: NewPaymentEntity) -> None:
        new_payment = NewPaymentMapper.to_model(payment)
        self.session.add(new_payment)
        
    async def get_pending_payment(self, user_id: int) -> None | PaymentEntity:
        result = await self.session.execute(
            select(Payment).where(Payment.user_id == user_id, Payment.status == "PENDING")
        )
        payment_model = result.scalar_one_or_none()
        if payment_model is None:
            return None 
        return PaymentMapper.from_model(payment_model)
    
    async def update_status(self, payment_id: int, new_status: PaymentStatus) -> None:
        payment_model = await self.session.get(Payment, payment_id)
        if payment_model is None:
            return None
        payment_model.status = new_status
        
    async def get_by_provider_payment_id(self, provider_payment_id: str) -> PaymentEntity | None:
        result = await self.session.execute(
            select(Payment).where(Payment.provider_payment_id == provider_payment_id)
        )
        payment_model = result.scalar_one_or_none()
        if payment_model is None:
            return None 
        return PaymentMapper.from_model(payment_model)
