"""Exceptions specific to volvooncall."""

from menuai.exceptions import menuaiError


class InvalidAuth(menuaiError):
    """Error to indicate there is invalid auth."""
