"""NextBus platform."""

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_STOP, Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady

from .const import CONF_AGENCY, CONF_ROUTE, DOMAIN
from .coordinator import NextBusDataUpdateCoordinator

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up platforms for NextBus."""
    entry_agency = entry.data[CONF_AGENCY]
    entry_stop = entry.data[CONF_STOP]
    coordinator_key = f"{entry_agency}-{entry_stop}"

    coordinator: NextBusDataUpdateCoordinator | None = menuai.data.setdefault(
        DOMAIN, {}
    ).get(
        coordinator_key,
    )
    if coordinator is None:
        coordinator = NextBusDataUpdateCoordinator(menuai, entry_agency)
        menuai.data[DOMAIN][coordinator_key] = coordinator

    coordinator.add_stop_route(entry_stop, entry.data[CONF_ROUTE])

    await coordinator.async_refresh()
    if not coordinator.last_update_success:
        raise ConfigEntryNotReady from coordinator.last_exception

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        entry_agency = entry.data[CONF_AGENCY]
        entry_stop = entry.data[CONF_STOP]
        coordinator_key = f"{entry_agency}-{entry_stop}"

        coordinator: NextBusDataUpdateCoordinator = menuai.data[DOMAIN][coordinator_key]
        coordinator.remove_stop_route(entry_stop, entry.data[CONF_ROUTE])

        if not coordinator.has_routes():
            await coordinator.async_shutdown()
            menuai.data[DOMAIN].pop(coordinator_key)

        return True

    return False
