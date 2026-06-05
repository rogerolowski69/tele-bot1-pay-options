import httpx

from apps.api.config import settings
from apps.api.db.models import OrderModel
from apps.api.exceptions import PaymentProviderError, ServiceUnavailableError


async def nowpayments_create_invoice(order: OrderModel) -> dict:
    """Create NOWPayments invoice. Returns {payment_url, invoice_id}."""
    if not settings.nowpayments_api_key:
        raise ServiceUnavailableError("NOWPayments is not configured")

    url = "https://api.nowpayments.io/v1/invoice"
    headers = {"x-api-key": settings.nowpayments_api_key, "Content-Type": "application/json"}
    body = {
        "price_amount": order.amount_minor / 100,
        "price_currency": order.currency.lower(),
        "order_id": str(order.id),
        "order_description": f"Order {order.id}",
        "ipn_callback_url": f"{settings.api_base_url}/api/webhooks/nowpayments",
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, headers=headers, json=body)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as exc:
        raise PaymentProviderError("NOWPayments invoice creation failed", details=str(exc)) from exc

    return {
        "payment_url": data["invoice_url"],
        "invoice_id": str(data.get("id", data.get("invoice_id", ""))),
    }
