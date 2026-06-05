import hashlib
import hmac

from apps.api.services.nowpayments_webhook import (
    build_nowpayments_signature,
    verify_nowpayments_signature,
)


def test_build_nowpayments_signature_sorted_keys():
    body = {"b": 2, "a": {"z": 1, "y": 2}, "c": [{"x": 1}]}
    secret = "test-secret"
    sig1 = build_nowpayments_signature(body, secret)
    sig2 = build_nowpayments_signature({"c": [{"x": 1}], "a": {"y": 2, "z": 1}, "b": 2}, secret)
    assert sig1 == sig2
    assert len(sig1) == 128


def test_verify_nowpayments_signature():
    body = {"payment_status": "finished", "order_id": "00000000-0000-0000-0000-000000000001"}
    secret = "ipn-secret"
    signature = build_nowpayments_signature(body, secret)
    assert verify_nowpayments_signature(body, signature, secret) is True
    assert verify_nowpayments_signature(body, "bad", secret) is False


def test_verify_rejects_tampered_body():
    body = {"payment_status": "finished", "order_id": "abc"}
    secret = "ipn-secret"
    signature = build_nowpayments_signature(body, secret)
    tampered = {**body, "order_id": "xyz"}
    assert verify_nowpayments_signature(tampered, signature, secret) is False
