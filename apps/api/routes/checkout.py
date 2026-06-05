from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.config import settings
from apps.api.db.session import get_db
from apps.api.deps import get_order_service, get_redis
from apps.api.services.nowpayments import nowpayments_create_invoice
from apps.api.services.orders import OrderService
from apps.api.services.telegram_payments import telegram_create_invoice_link
from apps.api.services.ton_payments import (
    find_matching_transaction,
    order_comment,
    resolve_amount_nanoton,
)
from packages.shared_types.payment import CheckoutResponseType, OrderStatus, PaymentMethod
from packages.telegram_auth import verify_telegram_init_data

router = APIRouter(prefix="/api", tags=["checkout"])


class CheckoutRequest(BaseModel):
    package_id: str
    method: PaymentMethod


class CheckoutResponse(BaseModel):
    type: CheckoutResponseType
    order_id: str
    url: str = ""
    recipient: str | None = None
    amount_nanoton: str | None = None
    comment: str | None = None
    network: str | None = None


class TonConfirmRequest(BaseModel):
    order_id: UUID


class TonConfirmResponse(BaseModel):
    status: str
    order_id: str
    tx_hash: str | None = None


class OrderStatusResponse(BaseModel):
    order_id: str
    status: str


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

    if payload.method == PaymentMethod.ton:
        if not settings.ton_receive_address:
            raise HTTPException(status_code=503, detail="TON payments not configured")

        try:
            amount_nanoton = resolve_amount_nanoton(
                package_id=package.id,
                currency=package.currency,
                amount_minor=package.amount_minor,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        comment = order_comment(str(order.id))
        await order_service.set_payment_terms(order, amount_minor=amount_nanoton, currency="TON")
        await order_service.mark_invoice_created(
            order,
            provider_invoice_id=comment,
            raw_payload={
                "recipient": settings.ton_receive_address,
                "amount_nanoton": amount_nanoton,
                "comment": comment,
                "network": settings.ton_network,
            },
        )
        return CheckoutResponse(
            type=CheckoutResponseType.ton_payment,
            order_id=str(order.id),
            recipient=settings.ton_receive_address,
            amount_nanoton=str(amount_nanoton),
            comment=comment,
            network=settings.ton_network,
        )

    raise HTTPException(status_code=400, detail="Unsupported payment method")


@router.post("/checkout/ton/confirm", response_model=TonConfirmResponse)
async def confirm_ton_payment(
    body: TonConfirmRequest,
    order_service: OrderService = Depends(get_order_service),
    x_telegram_init_data: str | None = Header(default=None, alias="X-Telegram-Init-Data"),
):
    tg_user = verify_telegram_init_data(x_telegram_init_data or "", settings.bot_token)
    order = await order_service.get_order_for_user(body.order_id, tg_user.id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.payment_method != PaymentMethod.ton.value:
        raise HTTPException(status_code=400, detail="Order is not a TON payment")

    if order.status == OrderStatus.paid.value:
        payment = order.raw_provider_payload.get("payment", {})
        return TonConfirmResponse(
            status=order.status,
            order_id=str(order.id),
            tx_hash=payment.get("hash"),
        )

    if order.status not in (OrderStatus.invoice_created.value, OrderStatus.pending.value):
        raise HTTPException(status_code=409, detail=f"Order status is {order.status}")

    invoice = order.raw_provider_payload
    recipient = invoice.get("recipient") or settings.ton_receive_address
    amount_nanoton = int(invoice.get("amount_nanoton", order.amount_minor))
    comment = invoice.get("comment") or order_comment(str(order.id))

    match = await find_matching_transaction(
        recipient=recipient,
        comment=comment,
        amount_nanoton=amount_nanoton,
        since=order.created_at,
    )
    if not match:
        return TonConfirmResponse(status=order.status, order_id=str(order.id))

    updated = await order_service.mark_paid(
        order.id,
        provider_charge_id=str(match.get("hash") or ""),
        amount_minor=amount_nanoton,
        currency="TON",
        raw_payload=match,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Order not found")

    return TonConfirmResponse(
        status=updated.status,
        order_id=str(updated.id),
        tx_hash=str(match.get("hash") or "") or None,
    )


@router.get("/checkout/{order_id}/status", response_model=OrderStatusResponse)
async def checkout_status(
    order_id: UUID,
    order_service: OrderService = Depends(get_order_service),
    x_telegram_init_data: str | None = Header(default=None, alias="X-Telegram-Init-Data"),
):
    tg_user = verify_telegram_init_data(x_telegram_init_data or "", settings.bot_token)
    order = await order_service.get_order_for_user(order_id, tg_user.id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return OrderStatusResponse(order_id=str(order.id), status=order.status)
