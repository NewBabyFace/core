"""The V2C integration."""

from __future__ import annotations

from pytrydan import Trydan

from menuai.const import CONF_HOST, Platform
from menuai.core import menuai
from menuai.helpers.httpx_client import get_async_client

from .coordinator import V2CConfigEntry, V2CUpdateCoordinator

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(menuai: menuai, entry: V2CConfigEntry) -> bool:
    """Set up V2C from a config entry."""

    trydan = Trydan(entry.data[CONF_HOST], get_async_client(menuai, verify_ssl=False))
    coordinator = V2CUpdateCoordinator(menuai, entry, trydan)

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    if coordinator.data.ID and entry.unique_id != coordinator.data.ID:
        menuai.config_entries.async_update_entry(entry, unique_id=coordinator.data.ID)

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: V2CConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
