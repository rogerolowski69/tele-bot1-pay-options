import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.api.config import settings
from apps.api.deps import get_order_service
from apps.api.main import app
from apps.api.services.ton_payments import order_comment, resolve_amount_nanoton
from packages.shared_types.payment import OrderStatus, PaymentMethod
from packages.telegram_auth import build_init_data


def test_resolve_amount_nanoton_from_ton_currency():
    assert resolve_amount_nanoton(package_id="x", currency="TON", amount_minor=123) == 123


def test_resolve_amount_nanoton_from_override(monkeypatch):
    monkeypatch.setattr(settings, "ton_package_prices", {"pro": 500000000})
    assert resolve_amount_nanoton(package_id="pro", currency="USD", amount_minor=500) == 500000000


def test_resolve_amount_nanoton_missing_price():
    with pytest.raises(ValueError, match="not priced"):
        resolve_amount_nanoton(package_id="pro", currency="USD", amount_minor=500)


async def test_checkout_ton_not_configured(client, bot_token: str, monkeypatch):
    monkeypatch.setattr(settings, "ton_receive_address", "")

    package = MagicMock()
    package.id = "pro"
    package.title = "Pro"
    package.description = "desc"
    package.amount_minor = 500
    package.currency = "USD"
    package.is_digital = False

    service = AsyncMock()
    service.get_package = AsyncMock(return_value=package)
    service.create_order = AsyncMock(
        return_value=MagicMock(id=uuid.uuid4(), created_at=datetime.now(UTC))
    )

    app.dependency_overrides[get_order_service] = lambda: service
    try:
        init_data = build_init_data(bot_token=bot_token, user_id=99)
        response = await client.post(
            "/api/checkout",
            json={"package_id": "pro", "method": "ton"},
            headers={"X-Telegram-Init-Data": init_data},
        )
        assert response.status_code == 503
    finally:
        app.dependency_overrides.clear()


async def test_checkout_ton_returns_payment_payload(client, bot_token: str, monkeypatch):
    monkeypatch.setattr(settings, "ton_receive_address", "EQTestMerchantAddress")
    monkeypatch.setattr(settings, "ton_network", "testnet")
    monkeypatch.setattr(settings, "ton_package_prices", {"pro": 500000000})

    order_id = uuid.uuid4()
    package = MagicMock()
    package.id = "pro"
    package.title = "Pro"
    package.description = "desc"
    package.amount_minor = 500
    package.currency = "USD"
    package.is_digital = False

    order = MagicMock()
    order.id = order_id
    order.created_at = datetime.now(UTC)

    service = AsyncMock()
    service.get_package = AsyncMock(return_value=package)
    service.create_order = AsyncMock(return_value=order)
    service.set_payment_terms = AsyncMock(return_value=order)
    service.mark_invoice_created = AsyncMock(return_value=order)

    app.dependency_overrides[get_order_service] = lambda: service
    try:
        init_data = build_init_data(bot_token=bot_token, user_id=99)
        response = await client.post(
            "/api/checkout",
            json={"package_id": "pro", "method": "ton"},
            headers={"X-Telegram-Init-Data": init_data},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "ton_payment"
        assert data["recipient"] == "EQTestMerchantAddress"
        assert data["amount_nanoton"] == "500000000"
        assert data["comment"] == order_comment(str(order_id))
        assert data["network"] == "testnet"
    finally:
        app.dependency_overrides.clear()


async def test_confirm_ton_marks_paid(client, bot_token: str, monkeypatch):
    monkeypatch.setattr(settings, "ton_receive_address", "EQTestMerchantAddress")

    order_id = uuid.uuid4()
    order = MagicMock()
    order.id = order_id
    order.status = OrderStatus.invoice_created.value
    order.payment_method = PaymentMethod.ton.value
    order.amount_minor = 500000000
    order.created_at = datetime.now(UTC)
    order.raw_provider_payload = {
        "recipient": "EQTestMerchantAddress",
        "amount_nanoton": 500000000,
        "comment": order_comment(str(order_id)),
        "network": "testnet",
    }

    paid_order = MagicMock()
    paid_order.id = order_id
    paid_order.status = OrderStatus.paid.value

    service = AsyncMock()
    service.get_order_for_user = AsyncMock(return_value=order)
    service.mark_paid = AsyncMock(return_value=paid_order)

    match = {"hash": "abc123", "value_nanoton": 500000000}

    app.dependency_overrides[get_order_service] = lambda: service
    with patch("apps.api.routes.checkout.find_matching_transaction", AsyncMock(return_value=match)):
        with patch("apps.api.services.orders.deliver_order", AsyncMock()):
            try:
                init_data = build_init_data(bot_token=bot_token, user_id=99)
                response = await client.post(
                    "/api/checkout/ton/confirm",
                    json={"order_id": str(order_id)},
                    headers={"X-Telegram-Init-Data": init_data},
                )
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "paid"
                assert data["tx_hash"] == "abc123"
                service.mark_paid.assert_awaited_once()
            finally:
                app.dependency_overrides.clear()
