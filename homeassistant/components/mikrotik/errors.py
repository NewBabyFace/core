"""Errors for the Mikrotik component."""

from menuai.exceptions import menuaiError


class CannotConnect(menuaiError):
    """Unable to connect to the hub."""


class LoginError(menuaiError):
    """Component got logged out."""
