"""The lg_soundbar component."""

import logging

from menuai import config_entries, core
from menuai.const import CONF_HOST, CONF_PORT, Platform
from menuai.exceptions import ConfigEntryNotReady

from .config_flow import test_connect
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.MEDIA_PLAYER]


async def async_setup_entry(
    menuai: core.menuai, entry: config_entries.ConfigEntry
) -> bool:
    """Set up platform from a ConfigEntry."""
    menuai.data.setdefault(DOMAIN, {})
    # Verify the device is reachable with the given config before setting up the platform
    try:
        await menuai.async_add_executor_job(
            test_connect, entry.data[CONF_HOST], entry.data[CONF_PORT]
        )
    except ConnectionError as err:
        raise ConfigEntryNotReady from err

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    menuai: core.menuai, entry: config_entries.ConfigEntry
) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
