"""The NZBGet integration."""

from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import config_validation as cv
from menuai.helpers.typing import ConfigType

from .const import DATA_COORDINATOR, DATA_UNDO_UPDATE_LISTENER, DOMAIN
from .coordinator import NZBGetDataUpdateCoordinator
from .services import async_setup_services

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
PLATFORMS = [Platform.SENSOR, Platform.SWITCH]


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up NZBGet integration."""

    async_setup_services(menuai)

    return True


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up NZBGet from a config entry."""
    menuai.data.setdefault(DOMAIN, {})

    coordinator = NZBGetDataUpdateCoordinator(menuai, entry)

    await coordinator.async_config_entry_first_refresh()

    undo_listener = entry.add_update_listener(_async_update_listener)

    menuai.data[DOMAIN][entry.entry_id] = {
        DATA_COORDINATOR: coordinator,
        DATA_UNDO_UPDATE_LISTENER: undo_listener,
    }

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        menuai.data[DOMAIN][entry.entry_id][DATA_UNDO_UPDATE_LISTENER]()
        menuai.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def _async_update_listener(menuai: menuai, entry: ConfigEntry) -> None:
    """Handle options update."""
    await menuai.config_entries.async_reload(entry.entry_id)
