import asyncio
import logging
import os
import sys

import httpx
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    ErrorEvent,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    PreCheckoutQuery,
    WebAppInfo,
)

DEBUG = os.environ.get("DEBUG", "").lower() in ("1", "true", "yes")
LOG_LEVEL = logging.DEBUG if DEBUG else logging.INFO

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    stream=sys.stdout,
    force=True,
)
logger = logging.getLogger("apps.bot")

BOT_TOKEN = os.environ["BOT_TOKEN"]
MINI_APP_URL = os.environ.get("MINI_APP_URL", "http://localhost:8082")
API_BASE_URL = os.environ.get("API_BASE_URL", "http://api:8000")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")

from apps.bot.handlers.market import market_router

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
dp.include_router(market_router)


@dp.errors()
async def global_error_handler(event: ErrorEvent):
    logger.exception("Unhandled bot error: %s", event.exception)
    if event.update.message:
        try:
            await event.update.message.answer("Something went wrong. Please try again later.")
        except Exception:
            logger.exception("Failed to send error reply")
    return True


@dp.message(CommandStart())
async def cmd_start(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Open Shop",
                    web_app=WebAppInfo(url=MINI_APP_URL),
                )
            ]
        ]
    )
    await message.answer(
        "Welcome! Open the shop or use market commands:\n"
        "/market — crypto, stocks, options, SEC fundamentals",
        reply_markup=keyboard,
    )


@dp.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    """Validate order exists before Telegram completes checkout."""
    payload = pre_checkout_query.invoice_payload
    if not payload.startswith("order:"):
        logger.warning("Rejected pre_checkout invalid payload=%s", payload)
        await pre_checkout_query.answer(ok=False, error_message="Invalid order")
        return
    await pre_checkout_query.answer(ok=True)


@dp.message(F.successful_payment)
async def successful_payment_handler(message: Message):
    """Forward trusted payment confirmation to API — never deliver from here alone."""
    payment = message.successful_payment
    if not payment:
        return

    body = {
        "order_payload": payment.invoice_payload,
        "provider_payment_charge_id": payment.provider_payment_charge_id,
        "total_amount": payment.total_amount,
        "currency": payment.currency,
        "raw": payment.model_dump(),
    }
    headers = {}
    if WEBHOOK_SECRET:
        headers["X-Webhook-Secret"] = WEBHOOK_SECRET

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{API_BASE_URL}/api/webhooks/telegram/payment",
                json=body,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as exc:
        logger.error("Payment webhook failed payload=%s error=%s", payment.invoice_payload, exc)
        await message.answer("Payment received but confirmation pending. Contact support.")
        return

    if data.get("status") == "paid":
        await message.answer("Payment confirmed! Your package is ready.")
    else:
        await message.answer("Payment received. We're verifying your order.")


async def wait_for_api(max_attempts: int = 30, delay_seconds: float = 2.0) -> None:
    for attempt in range(1, max_attempts + 1):
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{API_BASE_URL}/ready")
                if response.status_code == 200:
                    logger.info("API is ready")
                    return
        except httpx.HTTPError as exc:
            logger.debug("API not ready attempt=%s error=%s", attempt, exc)
        await asyncio.sleep(delay_seconds)
    logger.warning("API readiness check timed out — starting bot anyway")


async def main():
    await wait_for_api()
    logger.info("Starting bot polling debug=%s", DEBUG)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
