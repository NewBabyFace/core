"""Errors for assist satellite."""

from menuai.exceptions import menuaiError


class AssistSatelliteError(menuaiError):
    """Base class for assist satellite errors."""


class SatelliteBusyError(AssistSatelliteError):
    """Satellite is busy and cannot handle the request."""
