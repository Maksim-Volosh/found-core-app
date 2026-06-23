from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    CANCELLED = "cancelled"
    
    
class PaymentProviderType(str, Enum):
    STRIPE = "STRIPE"
    CRYPTO = "CRYPTO"


@dataclass
class PaymentSessionEntity:
    provider: PaymentProviderType
    provider_payment_id: str
    checkout_url: str


@dataclass
class NewPaymentEntity:
    user_id: int
    amount: int
    currency: str
    status: PaymentStatus
    provider: str
    provider_payment_id: Optional[str]
    
    
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