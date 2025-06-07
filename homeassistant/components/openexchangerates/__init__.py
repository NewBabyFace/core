"""The Open Exchange Rates integration."""

from __future__ import annotations

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_API_KEY, CONF_BASE, Platform
from menuai.core import menuai
from menuai.helpers.aiohttp_client import async_get_clientsession

from .const import BASE_UPDATE_INTERVAL, DOMAIN, LOGGER
from .coordinator import OpenexchangeratesCoordinator

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up Open Exchange Rates from a config entry."""
    api_key: str = entry.data[CONF_API_KEY]
    base: str = entry.data[CONF_BASE]

    # Create one coordinator per base currency per API key.
    existing_coordinators: dict[str, OpenexchangeratesCoordinator] = menuai.data.get(
        DOMAIN, {}
    )
    existing_coordinator_for_api_key = {
        existing_coordinator
        for config_entry_id, existing_coordinator in existing_coordinators.items()
        if (config_entry := menuai.config_entries.async_get_entry(config_entry_id))
        and config_entry.data[CONF_API_KEY] == api_key
    }

    # Adjust update interval by coordinators per API key.
    update_interval = BASE_UPDATE_INTERVAL * (len(existing_coordinator_for_api_key) + 1)
    coordinator = OpenexchangeratesCoordinator(
        menuai,
        entry,
        async_get_clientsession(menuai),
        api_key,
        base,
        update_interval,
    )

    LOGGER.debug("Coordinator update interval set to: %s", update_interval)

    # Set new interval on all coordinators for this API key.
    for existing_coordinator in existing_coordinator_for_api_key:
        existing_coordinator.update_interval = update_interval

    await coordinator.async_config_entry_first_refresh()

    menuai.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        menuai.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
