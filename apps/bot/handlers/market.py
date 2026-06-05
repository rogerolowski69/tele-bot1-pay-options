import logging
import os

import httpx
from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from packages.market_data.formatters import (
    format_crypto,
    format_fundamentals,
    format_options,
    format_stock,
)

logger = logging.getLogger("apps.bot.market")

API_BASE_URL = os.environ.get("API_BASE_URL", "http://api:8000")

market_router = Router(name="market")


async def _fetch(path: str) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(f"{API_BASE_URL}{path}")
        if response.status_code != 200:
            detail = response.json().get("detail", response.text)
            raise RuntimeError(str(detail))
        return response.json()


@market_router.message(Command("crypto"))
async def cmd_crypto(message: Message, command: CommandObject):
    symbol = (command.args or "bitcoin").split()[0]
    try:
        data = await _fetch(f"/api/market/crypto/{symbol}")
        await message.answer(format_crypto(data), parse_mode="Markdown")
    except Exception as exc:
        logger.exception("crypto command failed")
        await message.answer(f"Could not fetch crypto data: {exc}")


@market_router.message(Command("stock"))
async def cmd_stock(message: Message, command: CommandObject):
    if not command.args:
        await message.answer("Usage: /stock AAPL")
        return
    symbol = command.args.split()[0].upper()
    try:
        data = await _fetch(f"/api/market/stock/{symbol}")
        await message.answer(format_stock(data), parse_mode="Markdown")
    except Exception as exc:
        logger.exception("stock command failed")
        await message.answer(f"Could not fetch stock data: {exc}")


@market_router.message(Command("options"))
async def cmd_options(message: Message, command: CommandObject):
    if not command.args:
        await message.answer("Usage: /options AAPL")
        return
    symbol = command.args.split()[0].upper()
    try:
        data = await _fetch(f"/api/market/options/{symbol}")
        await message.answer(format_options(data), parse_mode="Markdown")
    except Exception as exc:
        logger.exception("options command failed")
        await message.answer(f"Could not fetch options chain: {exc}")


@market_router.message(Command("fundamentals", "sec"))
async def cmd_fundamentals(message: Message, command: CommandObject):
    if not command.args:
        await message.answer("Usage: /fundamentals AAPL  (or /sec AAPL)")
        return
    symbol = command.args.split()[0].upper()
    try:
        data = await _fetch(f"/api/market/fundamentals/{symbol}")
        await message.answer(format_fundamentals(data), parse_mode="Markdown")
    except Exception as exc:
        logger.exception("fundamentals command failed")
        await message.answer(f"Could not fetch fundamentals: {exc}")


@market_router.message(Command("market"))
async def cmd_market_help(message: Message):
    await message.answer(
        "*Market data commands*\n\n"
        "/crypto bitcoin — CoinGecko price\n"
        "/stock AAPL — quote (yfinance)\n"
        "/options AAPL — nearest option chain\n"
        "/fundamentals AAPL — SEC EDGAR + yfinance\n"
        "/sec AAPL — alias for /fundamentals\n\n"
        "_Fundamental lookups are Redis-cached. SEC requires SEC_USER_AGENT in .env._",
        parse_mode="Markdown",
    )
