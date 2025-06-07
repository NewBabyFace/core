"""Errors for the Netgear component."""

from menuai.exceptions import menuaiError


class NetgearException(menuaiError):
    """Base class for Netgear exceptions."""


class CannotLoginException(NetgearException):
    """Unable to login to the router."""
