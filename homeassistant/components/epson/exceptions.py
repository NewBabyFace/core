"""The errors of Epson integration."""

from menuai import exceptions


class CannotConnect(exceptions.menuaiError):
    """Error to indicate we cannot connect."""


class PoweredOff(exceptions.menuaiError):
    """Error to indicate projector is off."""
