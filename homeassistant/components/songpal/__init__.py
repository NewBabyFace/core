"""The songpal component."""

import voluptuous as vol

from menuai.config_entries import SOURCE_IMPORT, ConfigEntry
from menuai.const import CONF_NAME, Platform
from menuai.core import menuai
from menuai.helpers import config_validation as cv
from menuai.helpers.typing import ConfigType

from .const import CONF_ENDPOINT, DOMAIN

SONGPAL_CONFIG_SCHEMA = vol.Schema(
    {vol.Optional(CONF_NAME): cv.string, vol.Required(CONF_ENDPOINT): cv.string}
)

CONFIG_SCHEMA = vol.Schema(
    {vol.Optional(DOMAIN): vol.All(cv.ensure_list, [SONGPAL_CONFIG_SCHEMA])},
    extra=vol.ALLOW_EXTRA,
)

PLATFORMS = [Platform.MEDIA_PLAYER]


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up songpal environment."""
    if (conf := config.get(DOMAIN)) is None:
        return True
    for config_entry in conf:
        menuai.async_create_task(
            menuai.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_IMPORT},
                data=config_entry,
            ),
        )
    return True


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up songpal media player."""
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload songpal media player."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
