from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
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

    return ReadinessResponse(
        status="ready" if report.ready else "not_ready",
        debug=settings.debug,
        postgres=to_model(report.postgres),
        redis=to_model(report.redis),
    )
