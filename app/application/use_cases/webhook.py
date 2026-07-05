import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

import stripe

from app.application.services.payment import ProcessSuccessfulPaymentService
from app.domain.entities import SubscriptionEntity
from app.domain.entities.payment import PaymentStatus
from app.domain.entities.subscription import SubscriptionStatus
from app.domain.interfaces import IPaymentRepository, ISubscriptionRepository


class ProcessStripePaymentUseCase:
    def __init__(
        self,
        webhook_secret: str,
        payment_service: ProcessSuccessfulPaymentService,
    ):
        self.webhook_secret = webhook_secret
        self.payment_service = payment_service

    async def execute(self, payload: bytes, sig_header: str) -> bool:
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.webhook_secret
            )
        except (ValueError, stripe.SignatureVerificationError):
            return False

        if event["type"] != "checkout.session.completed":
            return True

        session_obj = event["data"]["object"]
        provider_payment_id = session_obj.id
        if not provider_payment_id:
            return False

        result = await self.payment_service.execute(provider_payment_id)
        return result


class ProcessCryptoPaymentUseCase:
    def __init__(
        self,
        payment_service: ProcessSuccessfulPaymentService,
        crypto_bot_token: str,
    ):
        self.crypto_bot_token = crypto_bot_token
        self.payment_service = payment_service

    async def execute(self, payload: bytes, sig_header: str) -> bool:
        try:
            secret = hashlib.sha256(self.crypto_bot_token.encode("utf-8")).digest()
            hmac_check = hmac.new(secret, payload, hashlib.sha256).hexdigest()

            if not hmac.compare_digest(hmac_check, sig_header):
                return False
        except Exception as e:
            return False

        try:
            event = json.loads(payload.decode("utf-8"))
        except Exception:
            return False

        if event.get("update_type") != "invoice_paid":
            return True

        provider_payment_id = str(event.get("payload", {}).get("invoice_id", ""))
        if not provider_payment_id:
            return False

        result = await self.payment_service.execute(provider_payment_id)
        return result
