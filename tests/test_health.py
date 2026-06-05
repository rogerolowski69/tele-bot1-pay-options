from unittest.mock import AsyncMock, MagicMock

import pytest

from apps.api.health import DependencyStatus, HealthReport


async def test_liveness(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["debug"] is False


async def test_readiness_not_ready_when_db_fails(client):
    from apps.api import deps
    from apps.api.db.session import get_db
    from apps.api.main import app

    async def broken_db():
        db = AsyncMock()
        db.execute = AsyncMock(side_effect=RuntimeError("db down"))
        yield db

    broken_redis = AsyncMock()
    broken_redis.ping = AsyncMock(side_effect=RuntimeError("redis down"))

    app.dependency_overrides[get_db] = broken_db
    app.dependency_overrides[deps.get_redis] = lambda: broken_redis
    try:
        response = await client.get("/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["postgres"]["ok"] is False
        assert data["redis"]["ok"] is False
    finally:
        app.dependency_overrides.clear()


def test_health_report_ready_property():
    report = HealthReport(
        postgres=DependencyStatus(ok=True, latency_ms=1.0),
        redis=DependencyStatus(ok=True, latency_ms=1.0),
    )
    assert report.ready is True

    report_bad = HealthReport(
        postgres=DependencyStatus(ok=False, error="fail"),
        redis=DependencyStatus(ok=True),
    )
    assert report_bad.ready is False
