import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

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
    with patch("apps.api.services.orders.deliver_order", AsyncMock()):
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
    with patch("apps.api.services.orders.deliver_order", AsyncMock()):
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


async def test_create_order_reuses_pending_invoice():
    paid_order = MagicMock()
    paid_order.status = OrderStatus.invoice_created.value

    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=paid_order)))
    service = OrderService(db, AsyncMock())

    result = await service.create_order(
        telegram_user_id=1,
        package=MagicMock(id="starter", currency="XTR", amount_minor=100),
        method=PaymentMethod.stars,
        idempotency_key="1:starter:stars",
    )
    assert result is paid_order
    db.add.assert_not_called()


async def test_create_order_new_after_paid():
    paid_order = MagicMock()
    paid_order.status = OrderStatus.paid.value

    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=paid_order)))
    db.commit = AsyncMock()
    db.refresh = AsyncMock(side_effect=lambda order: order)

    package = MagicMock()
    package.id = "starter"
    package.currency = "XTR"
    package.amount_minor = 100

    service = OrderService(db, AsyncMock())
    result = await service.create_order(
        telegram_user_id=1,
        package=package,
        method=PaymentMethod.stars,
        idempotency_key="1:starter:stars",
    )

    assert result is not paid_order
    db.add.assert_called_once()
    assert result.idempotency_key.startswith("1:starter:stars:")
