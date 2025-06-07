"""Errors for the Acmeda Pulse component."""

from menuai.exceptions import menuaiError


class PulseException(menuaiError):
    """Base class for Acmeda Pulse exceptions."""


class CannotConnect(PulseException):
    """Unable to connect to the bridge."""
