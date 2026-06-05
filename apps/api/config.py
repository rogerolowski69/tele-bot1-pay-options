import json

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    bot_token: str  # BOT_TOKEN
    telegram_provider_token: str = ""
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/telegram_payments"
    redis_url: str = "redis://localhost:6379/0"

    nowpayments_api_key: str = ""
    nowpayments_ipn_secret: str = ""
    btcpay_server_url: str = ""
    btcpay_store_id: str = ""
    btcpay_api_key: str = ""

    api_base_url: str = "http://localhost:8080"
    webhook_secret: str = ""  # optional shared secret for bot→api webhook
    debug_api_key: str = ""  # optional extra auth for /api/debug when DEBUG=true

    debug: bool = False
    log_level: str = "INFO"

    # Market data aggregator
    sec_user_agent: str = ""  # REQUIRED for SEC: "YourName email@example.com"
    coingecko_api_key: str = ""
    alpha_vantage_api_key: str = ""
    polygon_api_key: str = ""

    # TON wallet payments (TonConnect checkout)
    ton_receive_address: str = ""
    ton_network: str = "testnet"  # testnet | mainnet
    tonapi_key: str = ""
    # JSON map of package_id -> nanoton amount, e.g. {"pro": 500000000}
    ton_package_prices: dict[str, int] = {}

    # Order maintenance (expiry + delivery retries)
    order_expiry_hours: int = 24
    order_maintenance_interval_seconds: int = 300
    delivery_max_attempts: int = 5

    @field_validator("ton_package_prices", mode="before")
    @classmethod
    def parse_ton_package_prices(cls, value: object) -> dict[str, int]:
        if value is None or value == "":
            return {}
        if isinstance(value, dict):
            return {str(k): int(v) for k, v in value.items()}
        if isinstance(value, str):
            data = json.loads(value)
            return {str(k): int(v) for k, v in data.items()}
        raise TypeError("ton_package_prices must be a JSON object")


settings = Settings()
