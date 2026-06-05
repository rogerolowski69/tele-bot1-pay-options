"""NOWPayments IPN signature verification."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any


def _sort_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _sort_payload(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        return [_sort_payload(item) for item in value]
    return value


def build_nowpayments_signature(body: dict[str, Any], ipn_secret: str) -> str:
    """HMAC-SHA512 over recursively key-sorted JSON (NOWPayments IPN spec)."""
    sorted_body = _sort_payload(body)
    payload = json.dumps(sorted_body, separators=(",", ":"), ensure_ascii=False)
    return hmac.new(ipn_secret.encode(), payload.encode(), hashlib.sha512).hexdigest()


def verify_nowpayments_signature(body: dict[str, Any], signature: str, ipn_secret: str) -> bool:
    if not signature or not ipn_secret:
        return False
    expected = build_nowpayments_signature(body, ipn_secret)
    return hmac.compare_digest(expected, signature)
