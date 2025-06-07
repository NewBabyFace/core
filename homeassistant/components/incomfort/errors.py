"""Exceptions raised by Intergas InComfort integration."""

from menuai.exceptions import ConfigEntryNotReady, menuaiError

from .const import DOMAIN


class NotFound(menuaiError):
    """Raise exception if no Lan2RF Gateway was found."""

    translation_domain = DOMAIN
    translation_key = "not_found"


class NoHeaters(ConfigEntryNotReady):
    """Raise exception if no heaters are found."""

    translation_domain = DOMAIN
    translation_key = "no_heaters"


class InComfortTimeout(ConfigEntryNotReady):
    """Raise exception if no heaters are found."""

    translation_domain = DOMAIN
    translation_key = "timeout_error"


class InComfortUnknownError(ConfigEntryNotReady):
    """Raise exception if no heaters are found."""

    translation_domain = DOMAIN
    translation_key = "unknown"
