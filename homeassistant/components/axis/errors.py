"""Errors for the Axis component."""

from menuai.exceptions import menuaiError


class AxisException(menuaiError):
    """Base class for Axis exceptions."""


class AlreadyConfigured(AxisException):
    """Device is already configured."""


class AuthenticationRequired(AxisException):
    """Unknown error occurred."""


class CannotConnect(AxisException):
    """Unable to connect to the device."""


class UserLevel(AxisException):
    """User level too low."""
