from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.api.services.ton_payments import find_matching_transaction


async def test_find_matching_transaction_requires_exact_amount(monkeypatch):
    monkeypatch.setattr("apps.api.services.ton_payments.settings.tonapi_key", "")
    monkeypatch.setattr("apps.api.services.ton_payments.settings.ton_network", "testnet")

    order_id = "00000000-0000-0000-0000-000000000099"
    comment = f"order:{order_id}"
    since = datetime.now(UTC)

    overpay_tx = {
        "utime": int(since.timestamp()) + 10,
        "hash": "overpay",
        "in_msg": {
            "value": 600000000,
            "decoded_body": {"text": comment},
        },
    }
    exact_tx = {
        "utime": int(since.timestamp()) + 20,
        "hash": "exact",
        "in_msg": {
            "value": 500000000,
            "decoded_body": {"text": comment},
        },
    }

    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json = MagicMock(return_value={"transactions": [overpay_tx, exact_tx]})

    client = AsyncMock()
    client.get = AsyncMock(return_value=response)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)

    with patch("apps.api.services.ton_payments.httpx.AsyncClient", return_value=client):
        match = await find_matching_transaction(
            recipient="EQTest",
            comment=comment,
            amount_nanoton=500000000,
            since=since,
        )

    assert match is not None
    assert match["hash"] == "exact"
    assert match["value_nanoton"] == 500000000
