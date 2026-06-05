import httpx

from apps.api.config import settings
from apps.api.exceptions import PaymentProviderError, ServiceUnavailableError


async def telegram_create_invoice_link(
    *,
    order_id: str,
    title: str,
    description: str,
    payload: str,
    currency: str,
    provider_token: str,
    amount: int,
) -> str:
    """Create Telegram invoice link via Bot API createInvoiceLink."""
    url = f"https://api.telegram.org/bot{settings.bot_token}/createInvoiceLink"
    body = {
        "title": title,
        "description": description,
        "payload": payload,
        "currency": currency,
        "prices": [{"label": title, "amount": amount}],
    }
    if provider_token:
        body["provider_token"] = provider_token

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, json=body)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as exc:
        raise PaymentProviderError("Telegram invoice creation failed", details=str(exc)) from exc

    if not data.get("ok"):
        raise PaymentProviderError(
            data.get("description", "createInvoiceLink failed"),
            details=data,
        )
    return data["result"]
