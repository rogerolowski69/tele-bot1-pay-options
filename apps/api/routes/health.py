from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.config import settings
from apps.api.db.session import get_db
from apps.api.deps import get_redis
from apps.api.health import build_health_report

router = APIRouter(tags=["health"])


class DependencyHealth(BaseModel):
    ok: bool
    latency_ms: float | None = None
    error: str | None = None


class ReadinessResponse(BaseModel):
    status: str
    debug: bool
    postgres: DependencyHealth
    redis: DependencyHealth
    alembic_version: str | None = None
    order_timestamps_timestamptz: bool | None = None


async def _db_schema_status(db: AsyncSession) -> tuple[str | None, bool | None]:
    alembic_version: str | None = None
    all_timestamptz: bool | None = None
    try:
        version_result = await db.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
        alembic_version = version_result.scalar_one_or_none()
    except Exception:
        pass
    try:
        col_result = await db.execute(
            text("""
                SELECT data_type
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'orders'
                  AND column_name IN ('created_at', 'paid_at', 'failed_at', 'refunded_at')
            """)
        )
        types = [row[0] for row in col_result]
        if types:
            all_timestamptz = all(t == "timestamp with time zone" for t in types)
    except Exception:
        pass
    return alembic_version, all_timestamptz


@router.get("/health")
async def liveness():
    """Process is up — use for Docker liveness probes."""
    return {"status": "ok", "debug": settings.debug}


@router.get("/ready", response_model=ReadinessResponse)
async def readiness(
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis_client=Depends(get_redis),
):
    """Dependencies reachable — use for Docker readiness / depends_on."""
    report = await build_health_report(db, redis_client)
    if not report.ready:
        response.status_code = 503

    def to_model(dep) -> DependencyHealth:
        return DependencyHealth(ok=dep.ok, latency_ms=dep.latency_ms, error=dep.error)

    alembic_version, order_timestamps_timestamptz = await _db_schema_status(db)

    return ReadinessResponse(
        status="ready" if report.ready else "not_ready",
        debug=settings.debug,
        postgres=to_model(report.postgres),
        redis=to_model(report.redis),
        alembic_version=alembic_version,
        order_timestamps_timestamptz=order_timestamps_timestamptz,
    )
