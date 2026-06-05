import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.api.config import settings
from apps.api.services.fulfillment import deliver_order, try_deliver_order
from apps.api.services.order_maintenance import expire_stale_orders, retry_pending_deliveries
from packages.shared_types.payment import OrderStatus


async def test_expire_stale_orders(monkeypatch):
    monkeypatch.setattr(settings, "order_expiry_hours", 24)

    result_mock = MagicMock()
    result_mock.rowcount = 2

    db = AsyncMock()
    db.execute = AsyncMock(return_value=result_mock)
    db.commit = AsyncMock()

    count = await expire_stale_orders(db)
    assert count == 2
    db.commit.assert_awaited_once()


async def test_expire_stale_orders_disabled(monkeypatch):
    monkeypatch.setattr(settings, "order_expiry_hours", 0)
    db = AsyncMock()
    count = await expire_stale_orders(db)
    assert count == 0
    db.execute.assert_not_called()


async def test_retry_pending_deliveries():
    order_id = uuid.uuid4()
    order = MagicMock()
    order.id = order_id
    order.status = OrderStatus.paid.value
    order.package_id = "starter"
    order.raw_provider_payload = {}
    order.paid_at = datetime.now(UTC)

    package = MagicMock()

    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[order])))),
            MagicMock(scalar_one_or_none=MagicMock(return_value=package)),
        ]
    )

    with patch("apps.api.services.order_maintenance.try_deliver_order", AsyncMock(return_value=True)) as deliver:
        count = await retry_pending_deliveries(db, limit=5)
        assert count == 1
        deliver.assert_awaited_once()


async def test_deliver_order_records_failed_attempt():
    order = MagicMock()
    order.id = uuid.uuid4()
    order.status = OrderStatus.paid.value
    order.telegram_user_id = 123
    order.raw_provider_payload = {}

    package = MagicMock()
    package.title = "Starter"
    package.delivery_content = "Hi"
    package.description = ""

    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    with patch("apps.api.services.fulfillment.send_telegram_message", AsyncMock(side_effect=RuntimeError("network"))):
        sent = await deliver_order(order, package, db)

    assert sent is False
    delivery = order.raw_provider_payload["delivery"]
    assert delivery["attempts"] == 1
    assert "last_error_at" in delivery
    db.commit.assert_awaited()


async def test_try_deliver_order_never_raises():
    order = MagicMock()
    package = MagicMock()
    db = AsyncMock()

    with patch("apps.api.services.fulfillment.deliver_order", AsyncMock(side_effect=RuntimeError("boom"))):
        result = await try_deliver_order(order, package, db)
    assert result is False
