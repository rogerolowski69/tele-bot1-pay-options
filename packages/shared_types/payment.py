from enum import StrEnum


class PaymentMethod(StrEnum):
    stars = "stars"
    telegram_card = "telegram_card"
    crypto = "crypto"
    ton = "ton"


class OrderStatus(StrEnum):
    pending = "pending"
    invoice_created = "invoice_created"
    paid = "paid"
    failed = "failed"
    expired = "expired"
    cancelled = "cancelled"
    refunded = "refunded"


class PaymentProvider(StrEnum):
    telegram = "telegram"
    nowpayments = "nowpayments"
    btcpay = "btcpay"
    ton = "ton"
    manual = "manual"


class CheckoutResponseType(StrEnum):
    telegram_invoice = "telegram_invoice"
    external_url = "external_url"
    ton_payment = "ton_payment"
