import pytest

from packages.market_data.sec_edgar import SecEdgarClient, SecEdgarError


def test_sec_client_requires_email_in_user_agent():
    with pytest.raises(SecEdgarError, match="SEC_USER_AGENT"):
        SecEdgarClient("InvalidAgent")


def test_sec_client_accepts_valid_user_agent():
    client = SecEdgarClient("MyBot sbgreenland@gmail.com")
    assert "sbgreenland@gmail.com" in client._headers["User-Agent"]


@pytest.mark.asyncio
async def test_rate_limiter_allows_calls():
    from packages.market_data.rate_limit import AsyncRateLimiter

    limiter = AsyncRateLimiter(max_per_second=100)
    await limiter.acquire()
    await limiter.acquire()


def test_format_crypto():
    from packages.market_data.formatters import format_crypto

    text = format_crypto({"name": "Bitcoin", "symbol": "btc", "price": 50000, "change_24h_pct": 2.5})
    assert "Bitcoin" in text
    assert "50000" in text
