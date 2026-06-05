from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel

from apps.api.config import settings
from apps.api.deps import get_order_service
from apps.api.exceptions import NotFoundError
from apps.api.services.orders import OrderService

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


class TelegramPaymentConfirm(BaseModel):
    order_payload: str
    provider_payment_charge_id: str | None = None
    total_amount: int
    currency: str
    raw: dict


def verify_webhook_secret(x_webhook_secret: str | None = Header(default=None, alias="X-Webhook-Secret")) -> None:
    if settings.webhook_secret and x_webhook_secret != settings.webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")


@router.post("/telegram/payment")
async def telegram_payment_webhook(
    body: TelegramPaymentConfirm,
    _: None = Depends(verify_webhook_secret),
    order_service: OrderService = Depends(get_order_service),
):
    """Called by bot on successful_payment — backend is source of truth."""
    order = await order_service.get_by_payload(body.order_payload)
    if not order:
        raise NotFoundError("Order not found")

    updated = await order_service.mark_paid(
        order.id,
        provider_charge_id=body.provider_payment_charge_id,
        amount_minor=body.total_amount,
        currency=body.currency,
        raw_payload=body.raw,
    )
    if not updated:
        raise NotFoundError("Order not found")
    return {"status": updated.status, "order_id": str(updated.id)}


@router.post("/nowpayments")
async def nowpayments_webhook(
    request: Request,
    order_service: OrderService = Depends(get_order_service),
):
    import hashlib
    import hmac
    import uuid

    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON body") from exc

    signature = request.headers.get("x-nowpayments-sig", "")

    if settings.nowpayments_ipn_secret:
        sorted_payload = str(sorted(body.items()))
        expected = hmac.new(
            settings.nowpayments_ipn_secret.encode(),
            sorted_payload.encode(),
            hashlib.sha512,
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise HTTPException(status_code=401, detail="Invalid signature")

    payment_status = body.get("payment_status")
    if payment_status not in ("finished", "confirmed"):
        return {"ok": True, "ignored": payment_status}

    order_id_raw = body.get("order_id")
    if not order_id_raw:
        raise HTTPException(status_code=400, detail="Missing order_id")

    try:
        order_uuid = uuid.UUID(order_id_raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid order_id") from exc

    amount_minor = int(float(body.get("price_amount", 0)) * 100)
    currency = str(body.get("price_currency", "")).upper()

    updated = await order_service.mark_paid(
        order_uuid,
        provider_charge_id=str(body.get("payment_id", "")),
        amount_minor=amount_minor,
        currency=currency,
        raw_payload=body,
    )
    return {"ok": True, "status": updated.status if updated else "not_found"}
