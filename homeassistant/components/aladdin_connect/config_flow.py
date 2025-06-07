"""Config flow for Aladdin Connect integration."""

from menuai.config_entries import ConfigFlow

from . import DOMAIN


class AladdinConnectConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Aladdin Connect."""

    VERSION = 1
