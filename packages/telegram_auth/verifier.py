import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import parse_qsl


@dataclass(frozen=True)
class TelegramUser:
    id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None
    is_premium: bool | None = None


class InitDataError(Exception):
    pass


def verify_telegram_init_data(
    init_data: str,
    bot_token: str,
    max_age_seconds: int = 86400,
) -> TelegramUser:
    """Verify Telegram WebApp initData per official docs."""
    if not init_data:
        raise InitDataError("Missing init data")

    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = parsed.pop("hash", None)
    if not received_hash:
        raise InitDataError("Missing hash")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        raise InitDataError("Invalid hash")

    auth_date = int(parsed.get("auth_date", "0"))
    if time.time() - auth_date > max_age_seconds:
        raise InitDataError("Init data expired")

    user_raw = parsed.get("user")
    if not user_raw:
        raise InitDataError("Missing user")

    user_data = json.loads(user_raw)
    return TelegramUser(
        id=int(user_data["id"]),
        first_name=user_data.get("first_name", ""),
        last_name=user_data.get("last_name"),
        username=user_data.get("username"),
        language_code=user_data.get("language_code"),
        is_premium=user_data.get("is_premium"),
    )
