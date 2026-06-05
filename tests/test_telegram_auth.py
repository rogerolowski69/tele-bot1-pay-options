import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

import pytest

from packages.telegram_auth import InitDataError, build_init_data, verify_telegram_init_data


BOT_TOKEN = "123456789:AAH-test-token-for-unit-tests-only"


def test_build_and_verify_init_data():
    init_data = build_init_data(bot_token=BOT_TOKEN, user_id=42, first_name="Alice", username="alice")
    user = verify_telegram_init_data(init_data, BOT_TOKEN)
    assert user.id == 42
    assert user.first_name == "Alice"
    assert user.username == "alice"


def test_verify_rejects_missing_hash():
    with pytest.raises(InitDataError, match="Missing hash"):
        verify_telegram_init_data("user=%7B%22id%22%3A1%7D&auth_date=1", BOT_TOKEN)


def test_verify_rejects_invalid_hash():
    init_data = build_init_data(bot_token=BOT_TOKEN, user_id=1)
    parsed = dict(parse_qsl(init_data))
    parsed["hash"] = "deadbeef"
    tampered = "&".join(f"{k}={v}" for k, v in parsed.items())
    with pytest.raises(InitDataError, match="Invalid hash"):
        verify_telegram_init_data(tampered, BOT_TOKEN)


def test_verify_rejects_expired_init_data():
    old_date = int(time.time()) - 90000
    user = json.dumps({"id": 1, "first_name": "A"}, separators=(",", ":"))
    payload = {"user": user, "auth_date": str(old_date)}
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(payload.items()))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    payload["hash"] = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    init_data = "&".join(f"{k}={v}" for k, v in payload.items())
    with pytest.raises(InitDataError, match="expired"):
        verify_telegram_init_data(init_data, BOT_TOKEN, max_age_seconds=86400)
