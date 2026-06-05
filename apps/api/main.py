from contextlib import asynccontextmanager
import asyncio
import logging

import redis.asyncio as redis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.config import settings
from apps.api.db.session import SessionLocal
from apps.api.error_handlers import register_exception_handlers
from apps.api.logging_config import setup_logging
from apps.api.middleware import RequestLoggingMiddleware
from apps.api.routes import checkout, debug, health, internal, market, orders, packages, webhooks
from apps.api.services.order_maintenance import run_maintenance_cycle

logger = logging.getLogger(__name__)


async def _order_maintenance_loop(app: FastAPI) -> None:
    interval = max(settings.order_maintenance_interval_seconds, 60)
    while True:
        try:
            await asyncio.sleep(interval)
            async with SessionLocal() as db:
                await run_maintenance_cycle(db, app.state.redis)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Order maintenance cycle failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    app.state.redis = redis.from_url(settings.redis_url, decode_responses=True)
    maintenance_task = asyncio.create_task(_order_maintenance_loop(app))
    yield
    maintenance_task.cancel()
    try:
        await maintenance_task
    except asyncio.CancelledError:
        pass
    await app.state.redis.aclose()

app = FastAPI(
    title="Telegram Payments API",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
)

register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)

app.include_router(health.router)
app.include_router(checkout.router)
app.include_router(orders.router)
app.include_router(packages.router)
app.include_router(market.router)
app.include_router(webhooks.router)
app.include_router(internal.router)
app.include_router(debug.router)
