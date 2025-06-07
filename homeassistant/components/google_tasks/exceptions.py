"""Exceptions for Google Tasks api calls."""

from menuai.exceptions import menuaiError


class GoogleTasksApiError(menuaiError):
    """Error talking to the Google Tasks API."""
