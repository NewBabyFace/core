"""Custom exceptions for the devolo_home_control integration."""

from menuai.exceptions import menuaiError


class CredentialsInvalid(menuaiError):
    """Given credentials are invalid."""


class UuidChanged(menuaiError):
    """UUID of the user changed."""
