"""Errors for the Transmission component."""

from menuai.exceptions import menuaiError


class AuthenticationError(menuaiError):
    """Wrong Username or Password."""


class CannotConnect(menuaiError):
    """Unable to connect to client."""


class UnknownError(menuaiError):
    """Unknown Error."""
