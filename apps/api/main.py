from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.config import settings
from apps.api.error_handlers import register_exception_handlers
from apps.api.logging_config import setup_logging
from apps.api.middleware import RequestLoggingMiddleware
from apps.api.routes import checkout, debug, health, market, packages, webhooks


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    app.state.redis = redis.from_url(settings.redis_url, decode_responses=True)
    yield
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
app.include_router(packages.router)
app.include_router(market.router)
app.include_router(webhooks.router)
app.include_router(debug.router)
