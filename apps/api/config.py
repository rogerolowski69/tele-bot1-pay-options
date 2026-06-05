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

    api_base_url: str = "http://localhost:8082"
    webhook_secret: str = ""  # optional shared secret for bot→api webhook
    debug_api_key: str = ""  # optional extra auth for /api/debug when DEBUG=true

    debug: bool = False
    log_level: str = "INFO"

    # Market data aggregator
    sec_user_agent: str = ""  # REQUIRED for SEC: "YourName email@example.com"
    coingecko_api_key: str = ""
    alpha_vantage_api_key: str = ""
    polygon_api_key: str = ""


settings = Settings()
