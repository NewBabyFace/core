"""The notify_events component."""

import voluptuous as vol

from menuai.const import CONF_TOKEN, Platform
from menuai.core import menuai
from menuai.helpers import config_validation as cv, discovery
from menuai.helpers.typing import ConfigType

from .const import DOMAIN

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.Schema({vol.Required(CONF_TOKEN): cv.string})}, extra=vol.ALLOW_EXTRA
)


def setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the notify_events component."""

    menuai.data[DOMAIN] = config[DOMAIN]
    discovery.load_platform(menuai, Platform.NOTIFY, DOMAIN, {}, config)
    return True
