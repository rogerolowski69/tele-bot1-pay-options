import json
import logging
from typing import Any

import httpx

from packages.market_data.rate_limit import AsyncRateLimiter

logger = logging.getLogger(__name__)

SEC_BASE = "https://data.sec.gov"
SEC_TICKERS_URL = f"{SEC_BASE}/files/company_tickers.json"

# SEC allows max 10 requests/second — stay under with 8/sec buffer
_sec_limiter = AsyncRateLimiter(max_per_second=8.0)


class SecEdgarError(Exception):
    pass


class SecEdgarClient:
    def __init__(self, user_agent: str):
        if not user_agent or "@" not in user_agent:
            raise SecEdgarError(
                "SEC_USER_AGENT must include your name and email, e.g. "
                "'MyCompany admin@example.com'"
            )
        self._headers = {
            "User-Agent": user_agent,
            "Accept-Encoding": "gzip, deflate",
            "Accept": "application/json",
        }

    async def _get(self, url: str) -> dict[str, Any]:
        await _sec_limiter.acquire()
        async with httpx.AsyncClient(timeout=30, headers=self._headers) as client:
            response = await client.get(url)
            if response.status_code == 403:
                raise SecEdgarError("SEC returned 403 — check SEC_USER_AGENT header")
            if response.status_code == 429:
                raise SecEdgarError("SEC rate limit exceeded — slow down requests")
            response.raise_for_status()
            return response.json()

    async def get_company_facts(self, cik: str) -> dict[str, Any]:
        padded = str(cik).lstrip("0").zfill(10)
        url = f"{SEC_BASE}/api/xbrl/companyfacts/CIK{padded}.json"
        return await self._get(url)

    async def get_submissions(self, cik: str) -> dict[str, Any]:
        padded = str(cik).lstrip("0").zfill(10)
        url = f"{SEC_BASE}/submissions/CIK{padded}.json"
        return await self._get(url)

    async def lookup_cik(self, ticker: str) -> str | None:
        await _sec_limiter.acquire()
        async with httpx.AsyncClient(timeout=30, headers=self._headers) as client:
            response = await client.get(SEC_TICKERS_URL)
            response.raise_for_status()
            data = response.json()

        ticker_upper = ticker.upper()
        for entry in data.values():
            if str(entry.get("ticker", "")).upper() == ticker_upper:
                return str(entry["cik_str"]).zfill(10)
        return None

    async def get_facts_summary(self, ticker: str) -> dict[str, Any]:
        cik = await self.lookup_cik(ticker)
        if not cik:
            raise SecEdgarError(f"Ticker not found in SEC database: {ticker}")

        facts = await self.get_company_facts(cik)
        entity = facts.get("entityName", ticker.upper())
        us_gaap = facts.get("facts", {}).get("us-gaap", {})

        def latest_value(tag: str) -> dict[str, Any] | None:
            node = us_gaap.get(tag, {})
            units = node.get("units", {})
            for unit_values in units.values():
                if unit_values:
                    sorted_vals = sorted(unit_values, key=lambda x: x.get("end", ""), reverse=True)
                    return sorted_vals[0]
            return None

        assets = latest_value("Assets")
        revenue = latest_value("Revenues") or latest_value("RevenueFromContractWithCustomerExcludingAssessedTax")
        net_income = latest_value("NetIncomeLoss")

        return {
            "ticker": ticker.upper(),
            "cik": cik,
            "entity_name": entity,
            "assets": assets,
            "revenue": revenue,
            "net_income": net_income,
        }
