"""Errors for the Hue component."""

from menuai.exceptions import menuaiError


class HueException(menuaiError):
    """Base class for Hue exceptions."""


class CannotConnect(HueException):
    """Unable to connect to the bridge."""


class AuthenticationRequired(HueException):
    """Unknown error occurred."""
