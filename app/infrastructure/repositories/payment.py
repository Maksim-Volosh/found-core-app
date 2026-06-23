from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import NewPaymentEntity, NewUserEntity, UserEntity
from app.domain.interfaces import IPaymentRepository, IUserRepository
from app.infrastructure.mappers.payment import NewPaymentMapper
from app.infrastructure.mappers.user_mapper import NewUserMapper, UserMapper
from app.infrastructure.models import User
from app.infrastructure.models.payment import Payment


class SQLAlchemyPaymentRepository(IPaymentRepository):
    def __init__(self, session):
        self.session: AsyncSession = session
    
    async def create_payment(self, payment: NewPaymentEntity) -> None:
        new_payment = NewPaymentMapper.to_model(payment)
        self.session.add(new_payment)
        await self.session.commit()
        
    async def get_pending_payment(self, user_id: int):
        result = await self.session.execute(
            select(Payment).where(Payment.user_id == user_id, Payment.status == "PENDING")
        )
        payment_model = result.scalar_one_or_none()
        if payment_model is None:
            return None 
        return NewPaymentMapper.from_model(payment_model)
