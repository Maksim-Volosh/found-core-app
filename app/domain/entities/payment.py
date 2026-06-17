from datetime import datetime
from enum import Enum 
from dataclasses import dataclass
from typing import Optional

class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    CANCELED = "canceled"


@dataclass
class PaymentEntity:
    payment_id: int
    user_id: int
    amount: int
    currency: str
    status: PaymentStatus
    provider: str
    provider_payment_id: Optional[str]
    created_at: datetime
    updated_at: datetime