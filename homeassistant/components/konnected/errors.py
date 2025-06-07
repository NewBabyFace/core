"""Errors for the Konnected component."""

from menuai.exceptions import menuaiError


class KonnectedException(menuaiError):
    """Base class for Konnected exceptions."""


class CannotConnect(KonnectedException):
    """Unable to connect to the panel."""
