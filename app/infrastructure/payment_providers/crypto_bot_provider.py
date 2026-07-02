import logging
import aiohttp
from app.domain.interfaces.payment_provider import IPaymentProvider  # Твой интерфейс
from app.domain.entities import PaymentSessionEntity
from app.domain.entities.payment import PaymentProviderType
from app.core.config import settings

logger = logging.getLogger(__name__)

class CryptoBotPaymentProvider(IPaymentProvider):
    def __init__(self, api_key: str, is_testnet: bool):
        self.token = api_key
        self.base_url = (
            "https://testnet-pay.crypt.bot"
            if is_testnet
            else "https://pay.crypt.bot"
        )

    @property
    def provider(self) -> PaymentProviderType:
        return PaymentProviderType.CRYPTO

    async def create_checkout_session(self, user_id: int, price_in_cents: int, currency: str) -> PaymentSessionEntity:
        url = f"{self.base_url}/api/createInvoice"
        headers = {"Crypto-Pay-API-Token": self.token}
        
        amount = price_in_cents / 100.0
        
        asset = "USDT" if currency.upper() == "EUR" else currency.upper()

        payload = {
            "asset": asset,
            "amount": str(amount),
            "description": "Подписка в закрытый клуб",
            "payload": f"user_id:{user_id}",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("ok"):
                            result = data["result"]
                            
                            return PaymentSessionEntity(
                                provider=PaymentProviderType.CRYPTO,
                                provider_payment_id=str(result["invoice_id"]), 
                                checkout_url=result["pay_url"]  
                            )
                    
                    error_text = await response.text()
                    logger.error(f"Ошибка API CryptoBot ({response.status}): {error_text}")
                    raise Exception("Не удалось создать платежную сессию в CryptoBot")
                    
        except Exception as e:
            logger.error(f"Исключение при вызове CryptoBot API: {e}", exc_info=True)
            raise e