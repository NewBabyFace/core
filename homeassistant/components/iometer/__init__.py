"""The IOmeter integration."""

from __future__ import annotations

from iometer import IOmeterClient, IOmeterConnectionError

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_HOST, Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers.aiohttp_client import async_get_clientsession

from .coordinator import IOmeterConfigEntry, IOMeterCoordinator

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]


async def async_setup_entry(menuai: menuai, entry: IOmeterConfigEntry) -> bool:
    """Set up IOmeter from a config entry."""

    host = entry.data[CONF_HOST]
    session = async_get_clientsession(menuai)
    client = IOmeterClient(host=host, session=session)
    try:
        await client.get_current_status()
    except IOmeterConnectionError as err:
        raise ConfigEntryNotReady from err

    coordinator = IOMeterCoordinator(menuai, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
