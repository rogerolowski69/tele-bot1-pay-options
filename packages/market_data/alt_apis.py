import json
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class AlphaVantageClient:
    def __init__(self, api_key: str):
        self._api_key = api_key

    @property
    def enabled(self) -> bool:
        return bool(self._api_key)

    async def get_quote(self, symbol: str) -> dict[str, Any]:
        if not self.enabled:
            return {"error": "Alpha Vantage API key not configured"}
        url = "https://www.alphavantage.co/query"
        params = {"function": "GLOBAL_QUOTE", "symbol": symbol.upper(), "apikey": self._api_key}
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            quote = data.get("Global Quote", {})
            return {
                "symbol": quote.get("01. symbol"),
                "price": quote.get("05. price"),
                "change_pct": quote.get("10. change percent"),
                "source": "alpha_vantage",
            }


class PolygonClient:
    def __init__(self, api_key: str):
        self._api_key = api_key

    @property
    def enabled(self) -> bool:
        return bool(self._api_key)

    async def get_prev_close(self, symbol: str) -> dict[str, Any]:
        if not self.enabled:
            return {"error": "Polygon API key not configured"}
        url = f"https://api.polygon.io/v2/aggs/ticker/{symbol.upper()}/prev"
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(url, params={"apiKey": self._api_key})
            response.raise_for_status()
            results = response.json().get("results", [])
            if not results:
                return {"symbol": symbol.upper(), "error": "No data"}
            bar = results[0]
            return {
                "symbol": symbol.upper(),
                "close": bar.get("c"),
                "volume": bar.get("v"),
                "source": "polygon",
            }
