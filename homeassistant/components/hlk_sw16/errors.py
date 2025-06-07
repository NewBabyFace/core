"""Errors for the HLK-SW16 component."""

from menuai.exceptions import menuaiError


class SW16Exception(menuaiError):
    """Base class for HLK-SW16 exceptions."""


class CannotConnect(SW16Exception):
    """Unable to connect to the HLK-SW16."""
