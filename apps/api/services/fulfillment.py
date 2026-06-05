"""Deliver purchased packages via Telegram after payment is confirmed."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.config import settings
from apps.api.db.models import OrderModel, PackageModel
from packages.shared_types.payment import OrderStatus

logger = logging.getLogger(__name__)


def build_delivery_message(*, package: PackageModel, order: OrderModel) -> str:
    content = package.delivery_content.strip() or package.description.strip() or package.title
    return (
        f"✅ Payment confirmed!\n\n"
        f"📦 {package.title}\n"
        f"{content}\n\n"
        f"Order: {order.id}"
    )


async def send_telegram_message(chat_id: int, text: str) -> None:
    url = f"https://api.telegram.org/bot{settings.bot_token}/sendMessage"
    body = {"chat_id": chat_id, "text": text}
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url, json=body)
        response.raise_for_status()
        data = response.json()
    if not data.get("ok"):
        raise RuntimeError(data.get("description", "sendMessage failed"))


async def deliver_order(order: OrderModel, package: PackageModel, db: AsyncSession) -> bool:
    """Send delivery message once per order. Returns True if newly delivered."""
    if order.status != OrderStatus.paid.value:
        return False

    delivery_meta = order.raw_provider_payload.get("delivery") or {}
    if delivery_meta.get("sent_at"):
        return False

    attempts = int(delivery_meta.get("attempts", 0))
    if attempts >= settings.delivery_max_attempts:
        logger.warning("Delivery attempts exhausted for order %s", order.id)
        return False

    message = build_delivery_message(package=package, order=order)
    try:
        await send_telegram_message(order.telegram_user_id, message)
    except Exception:
        order.raw_provider_payload = {
            **order.raw_provider_payload,
            "delivery": {
                **delivery_meta,
                "attempts": attempts + 1,
                "last_error_at": datetime.now(UTC).isoformat(),
            },
        }
        await db.commit()
        await db.refresh(order)
        logger.exception("Failed to deliver order %s to user %s", order.id, order.telegram_user_id)
        return False

    order.raw_provider_payload = {
        **order.raw_provider_payload,
        "delivery": {
            "sent_at": datetime.now(UTC).isoformat(),
            "message": message,
            "attempts": attempts + 1,
        },
    }
    await db.commit()
    await db.refresh(order)
    logger.info("Delivered order %s to user %s", order.id, order.telegram_user_id)
    return True


async def try_deliver_order(order: OrderModel, package: PackageModel, db: AsyncSession) -> bool:
    """Best-effort delivery — never raises."""
    try:
        return await deliver_order(order, package, db)
    except Exception:
        logger.exception("Unexpected delivery error for order %s", order.id)
        return False
