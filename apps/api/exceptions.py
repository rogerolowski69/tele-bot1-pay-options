"""Shared application exceptions."""

from typing import Any


class AppError(Exception):
    """Base error with HTTP mapping."""

    status_code: int = 500
    code: str = "internal_error"

    def __init__(self, message: str, *, details: Any = None):
        super().__init__(message)
        self.message = message
        self.details = details


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class AuthError(AppError):
    status_code = 401
    code = "unauthorized"


class ValidationError(AppError):
    status_code = 400
    code = "validation_error"


class PaymentProviderError(AppError):
    status_code = 502
    code = "payment_provider_error"


class ServiceUnavailableError(AppError):
    status_code = 503
    code = "service_unavailable"
