from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

    
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
    months: int
    amount: int
    currency: str
    status: PaymentStatus
    provider: PaymentProviderType
    provider_payment_id: str
    provider_checkout_url: str
    
@dataclass
class PaymentEntity:
    payment_id: int
    user_id: int
    amount: int
    months: int
    currency: str
    status: PaymentStatus
    provider: PaymentProviderType
    provider_payment_id: str
    provider_checkout_url: str
    created_at: datetime
    updated_at: datetime