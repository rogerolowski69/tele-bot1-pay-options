import json
import logging
from typing import Any

import redis.asyncio as redis

from packages.market_data.alt_apis import AlphaVantageClient, PolygonClient
from packages.market_data.coingecko import CoinGeckoClient, CoinGeckoError
from packages.market_data.sec_edgar import SecEdgarClient, SecEdgarError
from packages.market_data.yfinance_client import YFinanceClient, YFinanceError

logger = logging.getLogger(__name__)


class MarketDataAggregator:
    """
    Two-zone aggregator:
      - Market zone: fast price/options (yfinance, CoinGecko)
      - Fundamental zone: SEC EDGAR XBRL (rate-limited, cached longer)
    """

    def __init__(
        self,
        *,
        redis_client: redis.Redis | None,
        sec_user_agent: str = "",
        coingecko_api_key: str = "",
        alpha_vantage_api_key: str = "",
        polygon_api_key: str = "",
    ):
        self._redis = redis_client
        self._yfinance = YFinanceClient()
        self._coingecko = CoinGeckoClient(coingecko_api_key)
        self._alpha = AlphaVantageClient(alpha_vantage_api_key)
        self._polygon = PolygonClient(polygon_api_key)
        self._sec: SecEdgarClient | None = None
        if sec_user_agent:
            try:
                self._sec = SecEdgarClient(sec_user_agent)
            except SecEdgarError as exc:
                logger.warning("SEC client disabled: %s", exc)

    async def _cache_get(self, key: str) -> dict[str, Any] | None:
        if not self._redis:
            return None
        raw = await self._redis.get(key)
        if raw:
            return json.loads(raw)
        return None

    async def _cache_set(self, key: str, data: dict[str, Any], ttl: int) -> None:
        if self._redis:
            await self._redis.set(key, json.dumps(data), ex=ttl)

    async def crypto(self, symbol: str) -> dict[str, Any]:
        cache_key = f"market:crypto:{symbol.lower()}"
        cached = await self._cache_get(cache_key)
        if cached:
            cached["cached"] = True
            return cached

        matches = await self._coingecko.search(symbol)
        if not matches:
            raise CoinGeckoError(f"No crypto match for '{symbol}'")
        coin_id = matches[0]["id"]
        data = await self._coingecko.get_price(coin_id)
        data["name"] = matches[0]["name"]
        data["symbol"] = matches[0]["symbol"]
        await self._cache_set(cache_key, data, ttl=60)
        return data

    async def stock(self, symbol: str) -> dict[str, Any]:
        cache_key = f"market:stock:{symbol.upper()}"
        cached = await self._cache_get(cache_key)
        if cached:
            cached["cached"] = True
            return cached

        try:
            data = await self._yfinance.get_quote(symbol)
        except YFinanceError:
            data = await self._alpha.get_quote(symbol)
        await self._cache_set(cache_key, data, ttl=60)
        return data

    async def options(self, symbol: str) -> dict[str, Any]:
        cache_key = f"market:options:{symbol.upper()}"
        cached = await self._cache_get(cache_key)
        if cached:
            cached["cached"] = True
            return cached

        data = await self._yfinance.get_options_summary(symbol)
        await self._cache_set(cache_key, data, ttl=300)
        return data

    async def fundamentals(self, symbol: str) -> dict[str, Any]:
        cache_key = f"market:fundamentals:{symbol.upper()}"
        cached = await self._cache_get(cache_key)
        if cached:
            cached["cached"] = True
            return cached

        result: dict[str, Any] = {"symbol": symbol.upper()}

        if self._sec:
            try:
                result["sec"] = await self._sec.get_facts_summary(symbol)
            except SecEdgarError as exc:
                result["sec_error"] = str(exc)

        try:
            result["yfinance"] = await self._yfinance.get_financials_summary(symbol)
        except YFinanceError as exc:
            result["yfinance_error"] = str(exc)

        if self._polygon.enabled:
            result["polygon"] = await self._polygon.get_prev_close(symbol)

        await self._cache_set(cache_key, result, ttl=3600)
        return result
