"""Config flow for Spider integration."""

from menuai.config_entries import ConfigFlow

from . import DOMAIN


class SpiderConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Spider."""

    VERSION = 1
