"""TON on-chain payment verification via TonAPI."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from apps.api.config import settings

logger = logging.getLogger(__name__)

ORDER_COMMENT_PREFIX = "order:"


def order_comment(order_id: str) -> str:
    return f"{ORDER_COMMENT_PREFIX}{order_id}"


def tonapi_base_url() -> str:
    if settings.ton_network == "mainnet":
        return "https://tonapi.io"
    return "https://testnet.tonapi.io"


def tonapi_headers() -> dict[str, str]:
    headers: dict[str, str] = {"Accept": "application/json"}
    if settings.tonapi_key:
        headers["Authorization"] = f"Bearer {settings.tonapi_key}"
    return headers


def resolve_amount_nanoton(*, package_id: str, currency: str, amount_minor: int) -> int:
    if currency == "TON":
        return amount_minor
    override = settings.ton_package_prices.get(package_id)
    if override is not None:
        return override
    raise ValueError(f"Package '{package_id}' is not priced for TON payment")


def _extract_comment(in_msg: dict[str, Any]) -> str | None:
    decoded_body = in_msg.get("decoded_body")
    if isinstance(decoded_body, dict):
        text = decoded_body.get("text") or decoded_body.get("comment")
        if isinstance(text, str) and text:
            return text

    msg_content = in_msg.get("msg_data")
    if isinstance(msg_content, dict):
        text = msg_content.get("text")
        if isinstance(text, str) and text:
            return text

    return None


def _incoming_value_nanoton(in_msg: dict[str, Any]) -> int:
    value = in_msg.get("value")
    if value is None:
        return 0
    return int(value)


async def find_matching_transaction(
    *,
    recipient: str,
    comment: str,
    amount_nanoton: int,
    since: datetime,
) -> dict[str, Any] | None:
    """Scan recent inbound transactions for matching comment + amount."""
    if not recipient:
        return None

    url = f"{tonapi_base_url()}/v2/blockchain/accounts/{recipient}/transactions"
    params = {"limit": 50}

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(url, params=params, headers=tonapi_headers())
        response.raise_for_status()
        payload = response.json()

    transactions = payload.get("transactions") or payload.get("items") or []
    since_ts = int(since.replace(tzinfo=UTC).timestamp())

    for tx in transactions:
        utime = int(tx.get("utime") or tx.get("timestamp") or 0)
        if utime and utime < since_ts:
            continue

        in_msg = tx.get("in_msg") or {}
        if not in_msg:
            continue

        tx_comment = _extract_comment(in_msg)
        if tx_comment != comment:
            continue

        value = _incoming_value_nanoton(in_msg)
        if value != amount_nanoton:
            continue

        tx_hash = tx.get("hash") or tx.get("transaction_id", {}).get("hash")
        return {
            "hash": tx_hash,
            "value_nanoton": value,
            "comment": tx_comment,
            "utime": utime,
            "raw": tx,
        }

    return None
