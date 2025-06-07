"""Exceptions for the dwd_weather_warnings integration."""

from menuai.exceptions import menuaiError


class EntityNotFoundError(menuaiError):
    """When a referenced entity was not found."""
