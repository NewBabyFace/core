"""Exceptions for fitbit API calls.

These exceptions exist to provide common exceptions for the async and sync client libraries.
"""

from menuai.exceptions import menuaiError


class FitbitApiException(menuaiError):
    """Error talking to the fitbit API."""


class FitbitAuthException(FitbitApiException):
    """Authentication related error talking to the fitbit API."""
