"""The simplepush component."""

from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import config_validation as cv, discovery
from menuai.helpers.typing import ConfigType

from .const import DATA_menuai_CONFIG, DOMAIN

PLATFORMS = [Platform.NOTIFY]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the simplepush component."""

    menuai.data[DATA_menuai_CONFIG] = config
    return True


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up simplepush from a config entry."""

    menuai.async_create_task(
        discovery.async_load_platform(
            menuai,
            Platform.NOTIFY,
            DOMAIN,
            dict(entry.data),
            menuai.data[DATA_menuai_CONFIG],
        )
    )

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
