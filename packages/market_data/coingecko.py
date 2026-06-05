import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

COINGECKO_BASE = "https://api.coingecko.com/api/v3"


class CoinGeckoError(Exception):
    pass


class CoinGeckoClient:
    def __init__(self, api_key: str = ""):
        self._api_key = api_key

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self._api_key:
            headers["x-cg-demo-api-key"] = self._api_key
        return headers

    async def get_price(self, coin_id: str, vs_currency: str = "usd") -> dict[str, Any]:
        url = f"{COINGECKO_BASE}/simple/price"
        params = {
            "ids": coin_id,
            "vs_currencies": vs_currency,
            "include_24hr_change": "true",
            "include_market_cap": "true",
            "include_24hr_vol": "true",
        }
        async with httpx.AsyncClient(timeout=20, headers=self._headers()) as client:
            response = await client.get(url, params=params)
            if response.status_code == 429:
                raise CoinGeckoError("CoinGecko rate limit — try again shortly")
            response.raise_for_status()
            data = response.json()
            if coin_id not in data:
                raise CoinGeckoError(f"Coin not found: {coin_id}")
            row = data[coin_id]
            return {
                "id": coin_id,
                "price": row.get(vs_currency),
                "change_24h_pct": row.get(f"{vs_currency}_24h_change"),
                "market_cap": row.get(f"{vs_currency}_market_cap"),
                "volume_24h": row.get(f"{vs_currency}_24h_vol"),
            }

    async def search(self, query: str) -> list[dict[str, Any]]:
        url = f"{COINGECKO_BASE}/search"
        async with httpx.AsyncClient(timeout=20, headers=self._headers()) as client:
            response = await client.get(url, params={"query": query})
            response.raise_for_status()
            coins = response.json().get("coins", [])
            return [{"id": c["id"], "symbol": c["symbol"], "name": c["name"]} for c in coins[:5]]
