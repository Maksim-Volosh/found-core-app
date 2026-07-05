from pydantic import BaseModel

from app.domain.entities.payment import PaymentProviderType


class PaymentRequest(BaseModel):
    user_id: int
    months: int
    provider_type: PaymentProviderType


class PaymentResponse(BaseModel):
    checkout_url: str
