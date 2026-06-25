from fastapi import APIRouter, Depends, Header, HTTPException, Request

from app.api.v1.schemas import PaymentRequest, PaymentResponse
from app.core.composition.container import Container
from app.core.composition.di import get_container
from app.domain.exceptions import NoPaymentRequired, UserNotFoundByUserId

router = APIRouter(prefix="/payment", tags=["Payment"])


@router.post("/create")
async def create_payment(
    payment_request: PaymentRequest,
    container: Container = Depends(get_container),
) -> PaymentResponse:
    try:
        checkout_url = await container.create_payment_use_case(
            provider_type=payment_request.provider_type
        ).execute(user_id=payment_request.user_id)
        return PaymentResponse(checkout_url=checkout_url)
    except UserNotFoundByUserId as e:
        raise HTTPException(status_code=404, detail=str(e))
    except NoPaymentRequired as e:
        raise HTTPException(status_code=202, detail=str(e))
    
@router.post("/webhook/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None),
    container: Container = Depends(get_container)
):
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")

    payload = await request.body()

    success = await container.process_successful_payment_use_case(
        ).execute(payload=payload, sig_header=stripe_signature)

    if not success:
        raise HTTPException(status_code=400, detail="Webhook processing failed")

    return {"status": "success"}