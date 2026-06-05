import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl, urlencode


def build_init_data(
    *,
    bot_token: str,
    user_id: int,
    first_name: str = "Test",
    username: str | None = "test_user",
    auth_date: int | None = None,
) -> str:
    """Build signed Telegram WebApp initData (testing / debug only)."""
    user: dict = {"id": user_id, "first_name": first_name}
    if username:
        user["username"] = username

    payload = {
        "user": json.dumps(user, separators=(",", ":")),
        "auth_date": str(auth_date or int(time.time())),
    }
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(payload.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    payload["hash"] = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode(payload)


def parse_init_data(init_data: str) -> dict[str, str]:
    return dict(parse_qsl(init_data, keep_blank_values=True))
