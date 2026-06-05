import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from apps.api.services.orders import OrderService
from packages.shared_types.payment import OrderStatus, PaymentMethod


async def test_mark_paid_idempotent_when_already_paid():
    order_id = uuid.uuid4()
    order = MagicMock()
    order.id = order_id
    order.status = OrderStatus.paid.value
    order.amount_minor = 100
    order.currency = "XTR"
    order.raw_provider_payload = {}

    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=order)))
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    redis = AsyncMock()
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock()

    service = OrderService(db, redis)
    result = await service.mark_paid(
        order_id,
        provider_charge_id="chg_1",
        amount_minor=100,
        currency="XTR",
        raw_payload={"test": True},
    )
    assert result.status == OrderStatus.paid.value
    db.commit.assert_not_called()


async def test_mark_paid_fails_on_amount_mismatch():
    order_id = uuid.uuid4()
    order = MagicMock()
    order.id = order_id
    order.status = OrderStatus.invoice_created.value
    order.amount_minor = 100
    order.currency = "XTR"
    order.raw_provider_payload = {}
    order.failed_at = None

    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=order)))
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    redis = AsyncMock()
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock()

    service = OrderService(db, redis)
    result = await service.mark_paid(
        order_id,
        provider_charge_id="chg_1",
        amount_minor=999,
        currency="XTR",
        raw_payload={"wrong": True},
    )
    assert result.status == OrderStatus.failed.value
    db.commit.assert_called_once()


def test_resolve_provider():
    assert OrderService._resolve_provider(PaymentMethod.stars).value == "telegram"
    assert OrderService._resolve_provider(PaymentMethod.crypto).value == "nowpayments"
