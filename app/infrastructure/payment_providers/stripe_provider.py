import stripe
from app.domain.entities import PaymentSessionEntity
from app.domain.entities.payment import PaymentProviderType
from app.domain.interfaces import IPaymentProvider


class StripePaymentProvider(IPaymentProvider):
    def __init__(self, api_key: str, success_url: str, cancel_url: str):
        self._api_key = api_key
        self._success_url = success_url
        self._cancel_url = cancel_url

    @property
    def provider(self) -> PaymentProviderType:
        return PaymentProviderType.STRIPE
    
    async def create_checkout_session(self, user_id: int, price_in_cents: int, currency: str) -> PaymentSessionEntity:
        session = await stripe.checkout.Session.create_async(
            api_key=self._api_key,
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": currency.lower(),
                        "product_data": {
                            "name": "Доступ в закрытый клуб (Подписка)",
                            "description": "Продление или активация подписки",
                        },
                        "unit_amount": price_in_cents,
                    },
                    "quantity": 1,
                },
            ],
            mode="payment",
            
            success_url=self._success_url,
            cancel_url=self._cancel_url,
            
            metadata={
                "user_id": str(user_id)
            }
        )
        
        return PaymentSessionEntity(
            provider=PaymentProviderType.STRIPE,
            provider_payment_id=session.id, 
            checkout_url=session.url if session.url else "",
        )