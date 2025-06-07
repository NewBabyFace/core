"""Zerproc lights integration."""

from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai

from .const import DATA_ADDRESSES, DATA_DISCOVERY_SUBSCRIPTION, DOMAIN

PLATFORMS = [Platform.LIGHT]


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up Zerproc from a config entry."""
    if DOMAIN not in menuai.data:
        menuai.data[DOMAIN] = {}
    if DATA_ADDRESSES not in menuai.data[DOMAIN]:
        menuai.data[DOMAIN][DATA_ADDRESSES] = set()

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Stop discovery
    unregister_discovery = menuai.data[DOMAIN].pop(DATA_DISCOVERY_SUBSCRIPTION, None)
    if unregister_discovery:
        unregister_discovery()

    menuai.data.pop(DOMAIN, None)

    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
