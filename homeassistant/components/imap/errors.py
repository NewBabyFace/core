"""Exceptions raised by IMAP integration."""

from menuai.exceptions import menuaiError


class InvalidAuth(menuaiError):
    """Raise exception for invalid credentials."""


class InvalidFolder(menuaiError):
    """Raise exception for invalid folder."""
