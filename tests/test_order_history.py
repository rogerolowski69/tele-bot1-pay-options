import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from apps.api.config import settings
from apps.api.deps import get_order_service
from apps.api.main import app
from apps.api.services.orders import OrderService
from packages.shared_types.payment import OrderStatus, PaymentMethod
from packages.telegram_auth import build_init_data


async def test_list_orders_me(client, bot_token: str):
    order_id = uuid.uuid4()
    order = MagicMock()
    order.id = order_id
    order.status = OrderStatus.paid.value
    order.package_id = "starter"
    order.payment_method = PaymentMethod.stars.value
    order.amount_minor = 100
    order.currency = "XTR"
    order.created_at = datetime.now(UTC)

    package = MagicMock()
    package.id = "starter"
    package.title = "Starter Package"

    service = AsyncMock()
    service.list_orders_for_user = AsyncMock(return_value=[order])
    service.get_package = AsyncMock(return_value=package)
    service.ton_payment_checkout_payload = MagicMock(return_value=None)

    app.dependency_overrides[get_order_service] = lambda: service
    try:
        init_data = build_init_data(bot_token=bot_token, user_id=42)
        response = await client.get(
            "/api/orders/me",
            headers={"X-Telegram-Init-Data": init_data},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["order_id"] == str(order_id)
        assert data[0]["package_title"] == "Starter Package"
        assert data[0]["status"] == "paid"
    finally:
        app.dependency_overrides.clear()


async def test_ton_payment_resume(client, bot_token: str, monkeypatch):
    monkeypatch.setattr(settings, "ton_receive_address", "EQTest")
    order_id = uuid.uuid4()
    order = MagicMock()
    order.id = order_id
    order.payment_method = PaymentMethod.ton.value
    order.status = OrderStatus.invoice_created.value
    order.raw_provider_payload = {
        "recipient": "EQTest",
        "amount_nanoton": 500000000,
        "comment": f"order:{order_id}",
        "network": "testnet",
    }

    service = AsyncMock()
    service.get_order_for_user = AsyncMock(return_value=order)
    service.ton_payment_checkout_payload = MagicMock(
        return_value=OrderService.ton_payment_checkout_payload(order)
    )

    app.dependency_overrides[get_order_service] = lambda: service
    try:
        init_data = build_init_data(bot_token=bot_token, user_id=42)
        response = await client.get(
            f"/api/orders/{order_id}/ton-payment",
            headers={"X-Telegram-Init-Data": init_data},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "ton_payment"
        assert data["amount_nanoton"] == "500000000"
        assert data["recipient"] == "EQTest"
    finally:
        app.dependency_overrides.clear()


def test_ton_payment_checkout_payload_pending():
    order = MagicMock()
    order.payment_method = PaymentMethod.ton.value
    order.status = OrderStatus.invoice_created.value
    order.id = uuid.uuid4()
    order.raw_provider_payload = {
        "recipient": "EQTest",
        "amount_nanoton": 100,
        "comment": "order:x",
        "network": "testnet",
    }
    payload = OrderService.ton_payment_checkout_payload(order)
    assert payload is not None
    assert payload["type"] == "ton_payment"


def test_ton_payment_checkout_payload_paid_returns_none():
    order = MagicMock()
    order.payment_method = PaymentMethod.ton.value
    order.status = OrderStatus.paid.value
    order.raw_provider_payload = {}
    assert OrderService.ton_payment_checkout_payload(order) is None
