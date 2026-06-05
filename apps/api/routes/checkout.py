from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.config import settings
from apps.api.db.session import get_db
from apps.api.deps import get_order_service, get_redis
from apps.api.services.nowpayments import nowpayments_create_invoice
from apps.api.services.orders import OrderService
from apps.api.services.telegram_payments import telegram_create_invoice_link
from packages.shared_types.payment import CheckoutResponseType, PaymentMethod
from packages.telegram_auth import verify_telegram_init_data

router = APIRouter(prefix="/api", tags=["checkout"])


class CheckoutRequest(BaseModel):
    package_id: str
    method: PaymentMethod


class CheckoutResponse(BaseModel):
    type: CheckoutResponseType
    url: str
    order_id: str


@router.post("/checkout", response_model=CheckoutResponse)
async def checkout(
    payload: CheckoutRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    order_service: OrderService = Depends(get_order_service),
    x_telegram_init_data: str | None = Header(default=None, alias="X-Telegram-Init-Data"),
):
    tg_user = verify_telegram_init_data(x_telegram_init_data or "", settings.bot_token)

    package = await order_service.get_package(payload.package_id)
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")

    if package.is_digital and payload.method != PaymentMethod.stars:
        raise HTTPException(
            status_code=400,
            detail="Digital goods must use Telegram Stars inside Telegram",
        )

    idempotency_key = request.headers.get("Idempotency-Key") or f"{tg_user.id}:{payload.package_id}:{payload.method}"

    order = await order_service.create_order(
        telegram_user_id=tg_user.id,
        package=package,
        method=payload.method,
        idempotency_key=idempotency_key,
    )

    invoice_payload = f"order:{order.id}"

    if payload.method == PaymentMethod.stars:
        invoice_url = await telegram_create_invoice_link(
            order_id=str(order.id),
            title=package.title,
            description=package.description,
            payload=invoice_payload,
            currency="XTR",
            provider_token="",
            amount=package.amount_minor,
        )
        await order_service.mark_invoice_created(order, provider_invoice_id=invoice_url)
        return CheckoutResponse(
            type=CheckoutResponseType.telegram_invoice,
            url=invoice_url,
            order_id=str(order.id),
        )

    if payload.method == PaymentMethod.telegram_card:
        if not settings.telegram_provider_token:
            raise HTTPException(status_code=503, detail="Telegram provider not configured")
        invoice_url = await telegram_create_invoice_link(
            order_id=str(order.id),
            title=package.title,
            description=package.description,
            payload=invoice_payload,
            currency=package.currency,
            provider_token=settings.telegram_provider_token,
            amount=package.amount_minor,
        )
        await order_service.mark_invoice_created(order, provider_invoice_id=invoice_url)
        return CheckoutResponse(
            type=CheckoutResponseType.telegram_invoice,
            url=invoice_url,
            order_id=str(order.id),
        )

    if payload.method == PaymentMethod.crypto:
        invoice = await nowpayments_create_invoice(order)
        await order_service.mark_invoice_created(
            order,
            provider_invoice_id=invoice["invoice_id"],
            raw_payload=invoice,
        )
        return CheckoutResponse(
            type=CheckoutResponseType.external_url,
            url=invoice["payment_url"],
            order_id=str(order.id),
        )

    raise HTTPException(status_code=400, detail="Unsupported payment method")
