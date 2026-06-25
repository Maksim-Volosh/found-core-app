from fastapi import APIRouter, Depends, Header, HTTPException, Request

from app.core.composition.container import Container
from app.core.composition.di import get_container

router = APIRouter(prefix="/webhook", tags=["Webhook"])

@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None),
    container: Container = Depends(get_container)
):
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")

    payload = await request.body()

    success = await container.get_process_successful_payment_use_case(
        ).execute(payload=payload, sig_header=stripe_signature)

    if not success:
        raise HTTPException(status_code=400, detail="Webhook processing failed")

    return {"status": "success"}