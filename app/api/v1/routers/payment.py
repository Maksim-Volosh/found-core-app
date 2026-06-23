from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.mappers.user import (map_user_entity_to_user_auth_schema,
                                     map_user_entity_to_user_schema,
                                     map_user_schema_to_entity)
from app.api.v1.schemas import (AuthUserRequest, PaymentRequest,
                                PaymentResponse, UserAuthResponse,
                                UserResponse)
from app.core.composition.container import Container
from app.core.composition.di import get_container
from app.domain.entities import NewUserEntity, UserSubscriptionEntity
from app.domain.entities.payment import PaymentProviderType
from app.domain.exceptions import (NoPaymentRequired, UserIsBanned,
                                   UserNotFoundByUserId)

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