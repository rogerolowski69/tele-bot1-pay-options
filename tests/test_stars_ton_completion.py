import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.api.config import settings
from apps.api.deps import get_order_service
from apps.api.main import app
from apps.api.services.fulfillment import build_delivery_message, deliver_order
from apps.api.services.orders import OrderService
from packages.shared_types.payment import OrderStatus, PaymentMethod


async def test_validate_pre_checkout_ok():
    order_id = uuid.uuid4()
    order = MagicMock()
    order.status = OrderStatus.invoice_created.value
    order.amount_minor = 100
    order.currency = "XTR"
    order.payment_method = PaymentMethod.stars.value

    db = AsyncMock()
    redis = AsyncMock()
    service = OrderService(db, redis)
    service.get_by_payload = AsyncMock(return_value=order)

    result = await service.validate_pre_checkout(
        invoice_payload=f"order:{order_id}",
        total_amount=100,
        currency="XTR",
    )
    assert result.ok is True


async def test_validate_pre_checkout_amount_mismatch():
    order = MagicMock()
    order.status = OrderStatus.invoice_created.value
    order.amount_minor = 100
    order.currency = "XTR"
    order.payment_method = PaymentMethod.stars.value

    service = OrderService(AsyncMock(), AsyncMock())
    service.get_by_payload = AsyncMock(return_value=order)

    result = await service.validate_pre_checkout(
        invoice_payload="order:00000000-0000-0000-0000-000000000001",
        total_amount=999,
        currency="XTR",
    )
    assert result.ok is False
    assert "Amount" in result.error


async def test_internal_pre_checkout_endpoint(client, monkeypatch):
    monkeypatch.setattr(settings, "webhook_secret", "")

    order = MagicMock()
    order.status = OrderStatus.invoice_created.value
    order.amount_minor = 100
    order.currency = "XTR"
    order.payment_method = PaymentMethod.stars.value

    service = AsyncMock()
    service.validate_pre_checkout = AsyncMock(
        return_value=type("R", (), {"ok": True, "error": ""})()
    )
    app.dependency_overrides[get_order_service] = lambda: service
    try:
        response = await client.post(
            "/api/internal/pre-checkout",
            json={
                "invoice_payload": "order:00000000-0000-0000-0000-000000000001",
                "total_amount": 100,
                "currency": "XTR",
            },
        )
        assert response.status_code == 200
        assert response.json()["ok"] is True
    finally:
        app.dependency_overrides.clear()


def test_build_delivery_message():
    package = MagicMock()
    package.title = "Starter"
    package.delivery_content = "Welcome!"
    package.description = "desc"
    order = MagicMock()
    order.id = uuid.uuid4()
    message = build_delivery_message(package=package, order=order)
    assert "Starter" in message
    assert "Welcome!" in message


async def test_deliver_order_sends_once():
    order_id = uuid.uuid4()
    order = MagicMock()
    order.id = order_id
    order.status = OrderStatus.paid.value
    order.telegram_user_id = 123
    order.raw_provider_payload = {}

    package = MagicMock()
    package.title = "Starter"
    package.delivery_content = "Enjoy"
    package.description = ""

    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    with patch("apps.api.services.fulfillment.send_telegram_message", AsyncMock()) as send:
        sent = await deliver_order(order, package, db)
        assert sent is True
        send.assert_awaited_once()

        order.raw_provider_payload = {"delivery": {"sent_at": datetime.now(UTC).isoformat()}}
        sent_again = await deliver_order(order, package, db)
        assert sent_again is False


async def test_mark_paid_triggers_delivery():
    order_id = uuid.uuid4()
    order = MagicMock()
    order.id = order_id
    order.status = OrderStatus.invoice_created.value
    order.amount_minor = 500000000
    order.currency = "TON"
    order.raw_provider_payload = {}
    order.package_id = "pro"
    order.paid_at = None
    order.provider_charge_id = None

    package = MagicMock()

    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=order)))
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    redis = AsyncMock()
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock()

    service = OrderService(db, redis)
    service.get_package = AsyncMock(return_value=package)

    with patch("apps.api.services.orders.deliver_order", AsyncMock()) as deliver:
        result = await service.mark_paid(
            order_id,
            provider_charge_id="txhash",
            amount_minor=500000000,
            currency="TON",
            raw_payload={"hash": "txhash"},
        )
        assert result.status == OrderStatus.paid.value
        deliver.assert_awaited_once()
