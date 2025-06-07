"""nuki integration helpers."""

from menuai import exceptions


def parse_id(hardware_id):
    """Parse Nuki ID."""
    return hex(hardware_id).split("x")[-1].upper()


class CannotConnect(exceptions.menuaiError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.menuaiError):
    """Error to indicate there is invalid auth."""


class NukiWebhookException(exceptions.menuaiError):
    """Error to indicate there was an issue with the webhook."""
