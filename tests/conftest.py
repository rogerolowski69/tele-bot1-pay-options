import os
from unittest.mock import AsyncMock

# Must be set before Settings is imported
os.environ.setdefault("BOT_TOKEN", "123456789:AAH-test-token-for-unit-tests-only")

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api import deps
from apps.api.config import settings
from apps.api.main import app


@pytest.fixture
def bot_token() -> str:
    return "123456789:AAH-test-token-for-unit-tests-only"


@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    redis.ping = AsyncMock(return_value=True)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock()
    return redis


@pytest.fixture
async def client(monkeypatch: pytest.MonkeyPatch, bot_token: str, mock_redis):
    monkeypatch.setattr(settings, "bot_token", bot_token)
    monkeypatch.setattr(settings, "debug", False)
    app.dependency_overrides[deps.get_redis] = lambda: mock_redis
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def debug_client(monkeypatch: pytest.MonkeyPatch, bot_token: str, mock_redis):
    monkeypatch.setattr(settings, "bot_token", bot_token)
    monkeypatch.setattr(settings, "debug", True)
    monkeypatch.setattr(settings, "debug_api_key", "")
    app.dependency_overrides[deps.get_redis] = lambda: mock_redis
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
