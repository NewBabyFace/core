"""Support for Mycroft AI."""

import voluptuous as vol

from menuai.const import CONF_HOST, Platform
from menuai.core import menuai
from menuai.helpers import config_validation as cv, discovery
from menuai.helpers.typing import ConfigType

DOMAIN = "mycroft"

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.Schema({vol.Required(CONF_HOST): cv.string})}, extra=vol.ALLOW_EXTRA
)


def setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the Mycroft component."""
    menuai.data[DOMAIN] = config[DOMAIN][CONF_HOST]
    discovery.load_platform(menuai, Platform.NOTIFY, DOMAIN, {}, config)
    return True
