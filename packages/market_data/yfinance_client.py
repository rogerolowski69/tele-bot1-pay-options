import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


class YFinanceError(Exception):
    pass


def _require_yfinance():
    try:
        import yfinance as yf  # noqa: PLC0415

        return yf
    except ImportError as exc:
        raise YFinanceError("yfinance is not installed") from exc


class YFinanceClient:
    """Wraps sync yfinance calls in asyncio.to_thread to avoid blocking the bot."""

    async def get_quote(self, symbol: str) -> dict[str, Any]:
        yf = _require_yfinance()

        def _fetch() -> dict[str, Any]:
            ticker = yf.Ticker(symbol.upper())
            info = ticker.fast_info
            return {
                "symbol": symbol.upper(),
                "price": getattr(info, "last_price", None) or getattr(info, "previous_close", None),
                "currency": getattr(info, "currency", "USD"),
                "market_cap": getattr(info, "market_cap", None),
                "volume": getattr(info, "last_volume", None),
            }

        return await asyncio.to_thread(_fetch)

    async def get_financials_summary(self, symbol: str) -> dict[str, Any]:
        yf = _require_yfinance()

        def _fetch() -> dict[str, Any]:
            ticker = yf.Ticker(symbol.upper())
            info = ticker.info or {}
            balance = ticker.balance_sheet
            income = ticker.financials

            total_assets = None
            if balance is not None and not balance.empty and "Total Assets" in balance.index:
                total_assets = float(balance.loc["Total Assets"].iloc[0])

            total_revenue = None
            if income is not None and not income.empty and "Total Revenue" in income.index:
                total_revenue = float(income.loc["Total Revenue"].iloc[0])

            return {
                "symbol": symbol.upper(),
                "name": info.get("longName") or info.get("shortName"),
                "sector": info.get("sector"),
                "market_cap": info.get("marketCap"),
                "pe_ratio": info.get("trailingPE"),
                "total_assets": total_assets,
                "total_revenue": total_revenue,
                "source": "yfinance",
            }

        return await asyncio.to_thread(_fetch)

    async def get_options_summary(self, symbol: str) -> dict[str, Any]:
        yf = _require_yfinance()

        def _fetch() -> dict[str, Any]:
            ticker = yf.Ticker(symbol.upper())
            expirations = list(ticker.options or [])
            if not expirations:
                return {"symbol": symbol.upper(), "expirations": [], "contracts": []}

            nearest = expirations[0]
            chain = ticker.option_chain(nearest)
            calls = chain.calls.head(5)
            puts = chain.puts.head(5)

            def rows(df, opt_type: str) -> list[dict[str, Any]]:
                out = []
                for _, row in df.iterrows():
                    out.append(
                        {
                            "type": opt_type,
                            "strike": float(row.get("strike", 0)),
                            "last": float(row.get("lastPrice", 0) or 0),
                            "volume": int(row.get("volume", 0) or 0),
                            "open_interest": int(row.get("openInterest", 0) or 0),
                        }
                    )
                return out

            return {
                "symbol": symbol.upper(),
                "nearest_expiration": nearest,
                "expirations_count": len(expirations),
                "calls": rows(calls, "call"),
                "puts": rows(puts, "put"),
                "source": "yfinance",
            }

        return await asyncio.to_thread(_fetch)
