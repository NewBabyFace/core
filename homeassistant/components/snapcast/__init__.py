"""Snapcast Integration."""

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_HOST, CONF_PORT
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady

from .const import DOMAIN, PLATFORMS
from .coordinator import SnapcastUpdateCoordinator


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up Snapcast from a config entry."""
    coordinator = SnapcastUpdateCoordinator(menuai, entry)

    try:
        await coordinator.async_config_entry_first_refresh()
    except OSError as ex:
        raise ConfigEntryNotReady(
            "Could not connect to Snapcast server at "
            f"{entry.data[CONF_HOST]}:{entry.data[CONF_PORT]}"
        ) from ex

    menuai.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        snapcast_data = menuai.data[DOMAIN].pop(entry.entry_id)
        # disconnect from server
        await snapcast_data.disconnect()
    return unload_ok
