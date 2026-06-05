import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from apps.api.config import settings
from apps.api.deps import get_order_service
from apps.api.main import app
from packages.shared_types.payment import PaymentMethod
from packages.telegram_auth import build_init_data


async def test_checkout_requires_init_data(client):
    response = await client.post("/api/checkout", json={"package_id": "starter", "method": "stars"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


async def test_checkout_rejects_invalid_init_data(client, bot_token: str):
    response = await client.post(
        "/api/checkout",
        json={"package_id": "starter", "method": "stars"},
        headers={"X-Telegram-Init-Data": "bad=data"},
    )
    assert response.status_code == 401


async def test_checkout_package_not_found(client, bot_token: str):
    service = AsyncMock()
    service.get_package = AsyncMock(return_value=None)
    app.dependency_overrides[get_order_service] = lambda: service
    try:
        init_data = build_init_data(bot_token=bot_token, user_id=99)
        response = await client.post(
            "/api/checkout",
            json={"package_id": "missing", "method": "stars"},
            headers={"X-Telegram-Init-Data": init_data},
        )
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


async def test_checkout_digital_requires_stars(client, bot_token: str):
    package = MagicMock()
    package.id = "starter"
    package.title = "Starter"
    package.description = "desc"
    package.amount_minor = 100
    package.currency = "XTR"
    package.is_digital = True

    service = AsyncMock()
    service.get_package = AsyncMock(return_value=package)

    app.dependency_overrides[get_order_service] = lambda: service
    try:
        init_data = build_init_data(bot_token=bot_token, user_id=99)
        response = await client.post(
            "/api/checkout",
            json={"package_id": "starter", "method": "crypto"},
            headers={"X-Telegram-Init-Data": init_data},
        )
        assert response.status_code == 400
        assert "Stars" in response.json()["error"]["message"]
    finally:
        app.dependency_overrides.clear()


async def test_debug_routes_hidden_when_not_debug(client):
    response = await client.get("/api/debug/health")
    assert response.status_code == 404


async def test_debug_init_data(debug_client, bot_token: str):
    response = await debug_client.post("/api/debug/init-data", json={"user_id": 777})
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == 777
    assert "hash=" in data["init_data"]


async def test_webhook_requires_secret_when_configured(client, monkeypatch):
    monkeypatch.setattr(settings, "webhook_secret", "topsecret")
    response = await client.post(
        "/api/webhooks/telegram/payment",
        json={
            "order_payload": "order:00000000-0000-0000-0000-000000000001",
            "total_amount": 100,
            "currency": "XTR",
            "raw": {},
        },
    )
    assert response.status_code == 401


async def test_webhook_order_not_found(client, monkeypatch):
    monkeypatch.setattr(settings, "webhook_secret", "")

    service = AsyncMock()
    service.get_by_payload = AsyncMock(return_value=None)
    app.dependency_overrides[get_order_service] = lambda: service
    try:
        response = await client.post(
            "/api/webhooks/telegram/payment",
            json={
                "order_payload": "order:00000000-0000-0000-0000-000000000001",
                "total_amount": 100,
                "currency": "XTR",
                "raw": {},
            },
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"
    finally:
        app.dependency_overrides.clear()
