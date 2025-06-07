"""Errors for the Media Player component."""

from menuai.exceptions import menuaiError


class MediaPlayerException(menuaiError):
    """Base class for Media Player exceptions."""


class BrowseError(MediaPlayerException):
    """Error while browsing."""


class SearchError(MediaPlayerException):
    """Error while searching."""
