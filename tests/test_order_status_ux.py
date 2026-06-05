from apps.api.services.orders import OrderService
from packages.shared_types.payment import OrderStatus


def test_status_message_for_failed_and_expired():
    assert OrderService.status_message_for(OrderStatus.failed.value)
    assert OrderService.status_message_for(OrderStatus.expired.value)
    assert OrderService.status_message_for(OrderStatus.paid.value) is None


def test_can_retry_checkout():
    assert OrderService.can_retry_checkout(OrderStatus.failed.value) is True
    assert OrderService.can_retry_checkout(OrderStatus.expired.value) is True
    assert OrderService.can_retry_checkout(OrderStatus.paid.value) is False
