from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.domain.entities.payment import PaymentProviderType
from app.domain.entities.subscription import SubscriptionStatus


class PaymentRequest(BaseModel):
    user_id: int
    provider_type: PaymentProviderType
    
    
class PaymentResponse(BaseModel):
    checkout_url: str