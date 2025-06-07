"""The Airgradient integration."""

from __future__ import annotations

from airgradient import AirGradientClient

from menuai.const import CONF_HOST, Platform
from menuai.core import menuai
from menuai.helpers.aiohttp_client import async_get_clientsession

from .coordinator import AirGradientConfigEntry, AirGradientCoordinator

PLATFORMS: list[Platform] = [
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.UPDATE,
]


async def async_setup_entry(menuai: menuai, entry: AirGradientConfigEntry) -> bool:
    """Set up Airgradient from a config entry."""

    client = AirGradientClient(
        entry.data[CONF_HOST], session=async_get_clientsession(menuai)
    )

    coordinator = AirGradientCoordinator(menuai, entry, client)

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    menuai: menuai, entry: AirGradientConfigEntry
) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
