import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta, timezone

import stripe

from app.application.services.payment import ProcessSuccessfulPaymentService
from app.domain.entities import SubscriptionEntity
from app.domain.entities.payment import PaymentStatus
from app.domain.entities.subscription import SubscriptionStatus
from app.domain.interfaces import IPaymentRepository, ISubscriptionRepository

logger = logging.getLogger(__name__)

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
            logger.info("Stripe webhook event received", extra={"event_type": event["type"]})
        except (ValueError, stripe.SignatureVerificationError) as exc:
            logger.warning("Stripe webhook signature verification failed", exc_info=exc)
            return False

        if event["type"] != "checkout.session.completed":
            logger.debug("Ignoring Stripe event type", extra={"event_type": event["type"]})
            return True

        session_obj = event["data"]["object"]
        provider_payment_id = session_obj.id
        if not provider_payment_id:
            logger.error("Stripe session object missing provider payment id", extra={"session_obj": session_obj})
            return False

        result = await self.payment_service.execute(provider_payment_id)
        logger.info(
            "Processed Stripe payment",
            extra={"provider_payment_id": provider_payment_id, "result": result},
        )
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
                logger.warning("Crypto webhook HMAC validation failed")
                return False
        except Exception as exc:
            logger.exception("Crypto webhook validation error", exc_info=exc)
            return False

        try:
            event = json.loads(payload.decode("utf-8"))
            logger.info("Crypto webhook payload decoded", extra={"event": event})
        except Exception as exc:
            logger.warning("Failed to decode crypto webhook payload", exc_info=exc)
            return False

        if event.get("update_type") != "invoice_paid":
            logger.debug("Ignoring crypto webhook update type", extra={"update_type": event.get("update_type")})
            return True

        provider_payment_id = str(event.get("payload", {}).get("invoice_id", ""))
        if not provider_payment_id:
            logger.error("Crypto webhook invoice_paid event missing invoice_id", extra={"event": event})
            return False

        result = await self.payment_service.execute(provider_payment_id)
        logger.info(
            "Processed crypto payment",
            extra={"provider_payment_id": provider_payment_id, "result": result},
        )
        return result
