"""Errors for media source."""

from menuai.exceptions import menuaiError


class MediaSourceError(menuaiError):
    """Base class for media source errors."""


class Unresolvable(MediaSourceError):
    """When media ID is not resolvable."""


class UnknownMediaSource(MediaSourceError, ValueError):
    """When media source is unknown."""
