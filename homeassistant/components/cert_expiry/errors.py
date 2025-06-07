"""Errors for the cert_expiry integration."""

from menuai.exceptions import menuaiError


class CertExpiryException(menuaiError):
    """Base class for cert_expiry exceptions."""


class TemporaryFailure(CertExpiryException):
    """Temporary failure has occurred."""


class ValidationFailure(CertExpiryException):
    """Certificate validation failure has occurred."""


class ResolveFailed(TemporaryFailure):
    """Name resolution failed."""


class ConnectionTimeout(TemporaryFailure):
    """Network connection timed out."""


class ConnectionRefused(TemporaryFailure):
    """Network connection refused."""
