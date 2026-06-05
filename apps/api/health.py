from dataclasses import dataclass

import redis.asyncio as redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class DependencyStatus:
    ok: bool
    latency_ms: float | None = None
    error: str | None = None


@dataclass
class HealthReport:
    postgres: DependencyStatus
    redis: DependencyStatus

    @property
    def ready(self) -> bool:
        return self.postgres.ok and self.redis.ok


async def check_postgres(db: AsyncSession) -> DependencyStatus:
    import time

    start = time.perf_counter()
    try:
        await db.execute(text("SELECT 1"))
        latency = (time.perf_counter() - start) * 1000
        return DependencyStatus(ok=True, latency_ms=round(latency, 2))
    except Exception as exc:
        return DependencyStatus(ok=False, error=str(exc))


async def check_redis(client: redis.Redis) -> DependencyStatus:
    import time

    start = time.perf_counter()
    try:
        await client.ping()
        latency = (time.perf_counter() - start) * 1000
        return DependencyStatus(ok=True, latency_ms=round(latency, 2))
    except Exception as exc:
        return DependencyStatus(ok=False, error=str(exc))


async def build_health_report(db: AsyncSession, redis_client: redis.Redis) -> HealthReport:
    pg = await check_postgres(db)
    rd = await check_redis(redis_client)
    return HealthReport(postgres=pg, redis=rd)
