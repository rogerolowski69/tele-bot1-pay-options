from fastapi import APIRouter, Depends, HTTPException, Query

from apps.api.deps import get_market_aggregator
from packages.market_data.aggregator import MarketDataAggregator
from packages.market_data.coingecko import CoinGeckoError
from packages.market_data.sec_edgar import SecEdgarError
from packages.market_data.yfinance_client import YFinanceError

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/crypto/{symbol}")
async def market_crypto(symbol: str, agg: MarketDataAggregator = Depends(get_market_aggregator)):
    try:
        return await agg.crypto(symbol)
    except CoinGeckoError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/stock/{symbol}")
async def market_stock(symbol: str, agg: MarketDataAggregator = Depends(get_market_aggregator)):
    try:
        return await agg.stock(symbol)
    except (YFinanceError, Exception) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/options/{symbol}")
async def market_options(symbol: str, agg: MarketDataAggregator = Depends(get_market_aggregator)):
    try:
        return await agg.options(symbol)
    except YFinanceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/fundamentals/{symbol}")
async def market_fundamentals(symbol: str, agg: MarketDataAggregator = Depends(get_market_aggregator)):
    try:
        return await agg.fundamentals(symbol)
    except SecEdgarError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/sec/{symbol}/facts")
async def sec_facts(symbol: str, agg: MarketDataAggregator = Depends(get_market_aggregator)):
    try:
        data = await agg.fundamentals(symbol)
        if "sec" not in data:
            raise HTTPException(status_code=503, detail=data.get("sec_error", "SEC not configured"))
        return data["sec"]
    except SecEdgarError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
