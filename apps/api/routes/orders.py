from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.config import settings
from apps.api.db.session import get_db
from apps.api.deps import get_order_service
from apps.api.services.orders import OrderService
from packages.shared_types.payment import OrderStatus, PaymentMethod
from packages.telegram_auth import verify_telegram_init_data

router = APIRouter(prefix="/api", tags=["orders"])


class PaymentConfigResponse(BaseModel):
    stars: bool = True
    ton: bool = False


class TonConfigDebugResponse(BaseModel):
    ton_receive_address_set: bool
    ton_receive_address_prefix: str | None
    ton_network: str
    ton_package_prices: dict[str, int]
    tonapi_key_set: bool
    ton_enabled: bool


class TimestampColumnDebugResponse(BaseModel):
    column_name: str
    data_type: str
    udt_name: str


class OrderTimestampColumnsDebugResponse(BaseModel):
    alembic_version: str | None
    columns: list[TimestampColumnDebugResponse]
    all_timestamptz: bool


class OrderDetailResponse(BaseModel):
    order_id: str
    status: str
    package_id: str
    package_title: str
    payment_method: str
    amount_minor: int
    currency: str
    delivery_message: str | None = None
    status_message: str | None = None
    can_retry: bool = False
    created_at: datetime | None = None
    can_resume_ton: bool = False


class OrderSummaryResponse(BaseModel):
    order_id: str
    status: str
    package_id: str
    package_title: str
    payment_method: str
    amount_minor: int
    currency: str
    status_message: str | None = None
    can_retry: bool = False
    created_at: datetime | None = None
    can_resume_ton: bool = False


class TonPaymentResumeResponse(BaseModel):
    type: str = "ton_payment"
    order_id: str
    recipient: str
    amount_nanoton: str
    comment: str
    network: str


def _order_detail(
    order,
    package,
    order_service: OrderService,
) -> OrderDetailResponse:
    delivery = order_service.delivery_message_for(order, package)
    ton_payload = OrderService.ton_payment_checkout_payload(order)
    return OrderDetailResponse(
        order_id=str(order.id),
        status=order.status,
        package_id=package.id,
        package_title=package.title,
        payment_method=order.payment_method,
        amount_minor=order.amount_minor,
        currency=order.currency,
        delivery_message=delivery if order.status == OrderStatus.paid.value else None,
        status_message=OrderService.status_message_for(order.status),
        can_retry=OrderService.can_retry_checkout(order.status),
        created_at=order.created_at,
        can_resume_ton=ton_payload is not None,
    )


def _verify_user(x_telegram_init_data: str | None) -> int:
    tg_user = verify_telegram_init_data(x_telegram_init_data or "", settings.bot_token)
    return tg_user.id


@router.get("/config/payments", response_model=PaymentConfigResponse)
async def payment_config():
    return PaymentConfigResponse(
        stars=True,
        ton=bool(settings.ton_receive_address),
    )


@router.get("/debug/ton-config", response_model=TonConfigDebugResponse)
async def debug_ton_config():
    """Temporary production-safe TON env diagnostic (no secrets)."""
    address = settings.ton_receive_address
    return TonConfigDebugResponse(
        ton_receive_address_set=bool(address),
        ton_receive_address_prefix=address[:2] if address else None,
        ton_network=settings.ton_network,
        ton_package_prices=settings.ton_package_prices,
        tonapi_key_set=bool(settings.tonapi_key),
        ton_enabled=bool(address),
    )


@router.get("/debug/order-timestamp-columns", response_model=OrderTimestampColumnsDebugResponse)
async def debug_order_timestamp_columns(db: AsyncSession = Depends(get_db)):
    """Production-safe check of orders.* timestamp column types (no secrets)."""
    col_result = await db.execute(
        text("""
            SELECT column_name, data_type, udt_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'orders'
              AND column_name IN ('created_at', 'paid_at', 'failed_at', 'refunded_at')
            ORDER BY column_name
        """)
    )
    columns = [
        TimestampColumnDebugResponse(
            column_name=row.column_name,
            data_type=row.data_type,
            udt_name=row.udt_name,
        )
        for row in col_result
    ]
    alembic_version: str | None = None
    try:
        version_result = await db.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
        alembic_version = version_result.scalar_one_or_none()
    except Exception:
        pass
    return OrderTimestampColumnsDebugResponse(
        alembic_version=alembic_version,
        columns=columns,
        all_timestamptz=all(c.data_type == "timestamp with time zone" for c in columns),
    )


@router.get("/orders/me", response_model=list[OrderSummaryResponse])
async def list_my_orders(
    order_service: OrderService = Depends(get_order_service),
    x_telegram_init_data: str | None = Header(default=None, alias="X-Telegram-Init-Data"),
):
    user_id = _verify_user(x_telegram_init_data)
    orders = await order_service.list_orders_for_user(user_id)
    summaries: list[OrderSummaryResponse] = []
    for order in orders:
        package = await order_service.get_package(order.package_id)
        if not package:
            continue
        ton_payload = OrderService.ton_payment_checkout_payload(order)
        summaries.append(
            OrderSummaryResponse(
                order_id=str(order.id),
                status=order.status,
                package_id=package.id,
                package_title=package.title,
                payment_method=order.payment_method,
                amount_minor=order.amount_minor,
                currency=order.currency,
                status_message=OrderService.status_message_for(order.status),
                can_retry=OrderService.can_retry_checkout(order.status),
                created_at=order.created_at,
                can_resume_ton=ton_payload is not None,
            )
        )
    return summaries


@router.get("/orders/{order_id}", response_model=OrderDetailResponse)
async def get_order_detail(
    order_id: UUID,
    order_service: OrderService = Depends(get_order_service),
    x_telegram_init_data: str | None = Header(default=None, alias="X-Telegram-Init-Data"),
):
    user_id = _verify_user(x_telegram_init_data)
    result = await order_service.get_order_with_package(order_id, user_id)
    if not result:
        raise HTTPException(status_code=404, detail="Order not found")
    order, package = result
    order = await order_service.ensure_delivery(order, package)
    return _order_detail(order, package, order_service)


@router.get("/orders/{order_id}/ton-payment", response_model=TonPaymentResumeResponse)
async def get_ton_payment_resume(
    order_id: UUID,
    order_service: OrderService = Depends(get_order_service),
    x_telegram_init_data: str | None = Header(default=None, alias="X-Telegram-Init-Data"),
):
    """Rebuild TON checkout payload for pending orders (survives page refresh)."""
    user_id = _verify_user(x_telegram_init_data)
    order = await order_service.get_order_for_user(order_id, user_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.payment_method != PaymentMethod.ton.value:
        raise HTTPException(status_code=400, detail="Order is not a TON payment")
    if order.status == OrderStatus.paid.value:
        raise HTTPException(status_code=409, detail="Order already paid")
    if order.status == OrderStatus.expired.value:
        raise HTTPException(status_code=409, detail="Order expired — start a new checkout from the shop")
    payload = OrderService.ton_payment_checkout_payload(order)
    if not payload:
        raise HTTPException(status_code=409, detail="Order cannot be resumed")
    return TonPaymentResumeResponse(**payload)
