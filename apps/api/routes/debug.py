import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.config import settings
from apps.api.db.models import OrderModel
from apps.api.db.session import get_db
from apps.api.deps import get_order_service, get_redis
from apps.api.health import build_health_report
from apps.api.services.orders import OrderService
from packages.telegram_auth.builder import build_init_data

router = APIRouter(prefix="/api/debug", tags=["debug"])


def require_debug(
    x_debug_key: str | None = Header(default=None, alias="X-Debug-Key"),
) -> None:
    if not settings.debug:
        raise HTTPException(status_code=404, detail="Not found")
    if settings.debug_api_key and x_debug_key != settings.debug_api_key:
        raise HTTPException(status_code=401, detail="Invalid debug key")


class InitDataRequest(BaseModel):
    user_id: int = 123456789
    first_name: str = "Debug"
    username: str = "debug_user"


class InitDataResponse(BaseModel):
    init_data: str
    user_id: int


class SimulatePaymentRequest(BaseModel):
    provider_payment_charge_id: str = Field(default_factory=lambda: f"debug_{uuid.uuid4().hex[:12]}")


class OrderSummary(BaseModel):
    id: str
    telegram_user_id: int
    package_id: str
    payment_method: str
    provider: str
    amount_minor: int
    currency: str
    status: str
    created_at: str
    paid_at: str | None


@router.get("/health")
async def debug_health(
    response: Response,
    _: None = Depends(require_debug),
    db: AsyncSession = Depends(get_db),
    redis_client=Depends(get_redis),
):
    report = await build_health_report(db, redis_client)
    if not report.ready:
        response.status_code = 503
    return {
        "debug": True,
        "status": "ready" if report.ready else "not_ready",
        "postgres": {"ok": report.postgres.ok, "error": report.postgres.error},
        "redis": {"ok": report.redis.ok, "error": report.redis.error},
        "docs": "/docs",
    }


@router.post("/init-data", response_model=InitDataResponse)
async def create_init_data(body: InitDataRequest, _: None = Depends(require_debug)):
    """Generate valid Telegram initData for local API testing (curl, Postman)."""
    init_data = build_init_data(
        bot_token=settings.bot_token,
        user_id=body.user_id,
        first_name=body.first_name,
        username=body.username,
    )
    return InitDataResponse(init_data=init_data, user_id=body.user_id)


@router.get("/orders", response_model=list[OrderSummary])
async def list_orders(
    limit: int = 50,
    _: None = Depends(require_debug),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(OrderModel).order_by(OrderModel.created_at.desc()).limit(min(limit, 200))
    )
    orders = result.scalars().all()
    return [
        OrderSummary(
            id=str(o.id),
            telegram_user_id=o.telegram_user_id,
            package_id=o.package_id,
            payment_method=o.payment_method,
            provider=o.provider,
            amount_minor=o.amount_minor,
            currency=o.currency,
            status=o.status,
            created_at=o.created_at.isoformat() if o.created_at else "",
            paid_at=o.paid_at.isoformat() if o.paid_at else None,
        )
        for o in orders
    ]


@router.get("/orders/{order_id}", response_model=OrderSummary)
async def get_order(
    order_id: uuid.UUID,
    _: None = Depends(require_debug),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(OrderModel).where(OrderModel.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return OrderSummary(
        id=str(order.id),
        telegram_user_id=order.telegram_user_id,
        package_id=order.package_id,
        payment_method=order.payment_method,
        provider=order.provider,
        amount_minor=order.amount_minor,
        currency=order.currency,
        status=order.status,
        created_at=order.created_at.isoformat() if order.created_at else "",
        paid_at=order.paid_at.isoformat() if order.paid_at else None,
    )


@router.post("/orders/{order_id}/simulate-payment")
async def simulate_payment(
    order_id: uuid.UUID,
    body: SimulatePaymentRequest,
    _: None = Depends(require_debug),
    db: AsyncSession = Depends(get_db),
    order_service: OrderService = Depends(get_order_service),
):
    """Mark an order paid without Telegram — debug only, never enable in production."""
    result = await db.execute(select(OrderModel).where(OrderModel.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    updated = await order_service.mark_paid(
        order.id,
        provider_charge_id=body.provider_payment_charge_id,
        amount_minor=order.amount_minor,
        currency=order.currency,
        raw_payload={"source": "debug_simulate_payment"},
    )
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update order")
    return {"status": updated.status, "order_id": str(order_id)}
