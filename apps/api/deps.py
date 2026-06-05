import redis.asyncio as redis
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.config import settings
from apps.api.db.session import get_db
from apps.api.services.orders import OrderService
from packages.market_data.aggregator import MarketDataAggregator


def get_redis(request: Request) -> redis.Redis:
    return request.app.state.redis


async def get_order_service(
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
) -> OrderService:
    return OrderService(db, redis_client)


def get_market_aggregator(redis_client: redis.Redis = Depends(get_redis)) -> MarketDataAggregator:
    return MarketDataAggregator(
        redis_client=redis_client,
        sec_user_agent=settings.sec_user_agent,
        coingecko_api_key=settings.coingecko_api_key,
        alpha_vantage_api_key=settings.alpha_vantage_api_key,
        polygon_api_key=settings.polygon_api_key,
    )
