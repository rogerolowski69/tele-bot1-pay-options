from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from apps.api.config import settings
from apps.api.deps import get_order_service
from apps.api.services.orders import OrderService

router = APIRouter(prefix="/api/internal", tags=["internal"])


class PreCheckoutRequest(BaseModel):
    invoice_payload: str
    total_amount: int
    currency: str


class PreCheckoutResponse(BaseModel):
    ok: bool
    error: str = ""


def verify_internal_secret(x_webhook_secret: str | None = Header(default=None, alias="X-Webhook-Secret")) -> None:
    if settings.webhook_secret and x_webhook_secret != settings.webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")


@router.post("/pre-checkout", response_model=PreCheckoutResponse)
async def validate_pre_checkout(
    body: PreCheckoutRequest,
    _: None = Depends(verify_internal_secret),
    order_service: OrderService = Depends(get_order_service),
):
    """Called by bot before approving Telegram pre_checkout_query."""
    result = await order_service.validate_pre_checkout(
        invoice_payload=body.invoice_payload,
        total_amount=body.total_amount,
        currency=body.currency,
    )
    return PreCheckoutResponse(ok=result.ok, error=result.error)
