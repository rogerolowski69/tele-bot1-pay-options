"""Background order expiry and delivery retries."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

import redis.asyncio as redis
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.config import settings
from apps.api.db.models import OrderModel, PackageModel
from apps.api.services.fulfillment import try_deliver_order
from packages.shared_types.payment import OrderStatus

logger = logging.getLogger(__name__)

_OPEN_ORDER_STATUSES = (
    OrderStatus.pending.value,
    OrderStatus.invoice_created.value,
)


async def expire_stale_orders(db: AsyncSession) -> int:
    """Mark old unpaid orders as expired."""
    if settings.order_expiry_hours <= 0:
        return 0

    cutoff = datetime.now(UTC) - timedelta(hours=settings.order_expiry_hours)
    result = await db.execute(
        update(OrderModel)
        .where(
            OrderModel.status.in_(_OPEN_ORDER_STATUSES),
            OrderModel.created_at < cutoff,
        )
        .values(status=OrderStatus.expired.value)
    )
    await db.commit()
    count = result.rowcount or 0
    if count:
        logger.info("Expired %s stale orders", count)
    return count


async def retry_pending_deliveries(db: AsyncSession, *, limit: int = 20) -> int:
    """Retry Telegram delivery for paid orders that were not sent yet."""
    result = await db.execute(
        select(OrderModel)
        .where(OrderModel.status == OrderStatus.paid.value)
        .order_by(OrderModel.paid_at.asc().nullsfirst())
        .limit(limit)
    )
    orders = list(result.scalars().all())
    delivered = 0

    for order in orders:
        delivery_meta = order.raw_provider_payload.get("delivery") or {}
        if delivery_meta.get("sent_at"):
            continue
        if int(delivery_meta.get("attempts", 0)) >= settings.delivery_max_attempts:
            continue

        package_result = await db.execute(
            select(PackageModel).where(PackageModel.id == order.package_id, PackageModel.active.is_(True))
        )
        package = package_result.scalar_one_or_none()
        if not package:
            continue

        if await try_deliver_order(order, package, db):
            delivered += 1

    if delivered:
        logger.info("Retried delivery for %s orders", delivered)
    return delivered


async def run_maintenance_cycle(db: AsyncSession, redis_client: redis.Redis) -> None:
    del redis_client  # reserved for future distributed locks
    await expire_stale_orders(db)
    await retry_pending_deliveries(db)
