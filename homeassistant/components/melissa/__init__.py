"""Support for Melissa climate."""

from melissa import AsyncMelissa
import voluptuous as vol

from menuai.const import CONF_PASSWORD, CONF_USERNAME, Platform
from menuai.core import menuai
from menuai.helpers import config_validation as cv
from menuai.helpers.discovery import async_load_platform
from menuai.helpers.typing import ConfigType

DOMAIN = "melissa"
DATA_MELISSA = "MELISSA"


CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the Melissa Climate component."""
    conf = config[DOMAIN]
    username = conf.get(CONF_USERNAME)
    password = conf.get(CONF_PASSWORD)
    api = AsyncMelissa(username=username, password=password)
    await api.async_connect()
    menuai.data[DATA_MELISSA] = api

    menuai.async_create_task(
        async_load_platform(menuai, Platform.CLIMATE, DOMAIN, {}, config)
    )
    return True
