"""The FireServiceRota integration."""

from __future__ import annotations

from datetime import timedelta

from menuai.const import Platform
from menuai.core import menuai

from .coordinator import (
    FireServiceConfigEntry,
    FireServiceRotaClient,
    FireServiceUpdateCoordinator,
)

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=60)

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR, Platform.SWITCH]


async def async_setup_entry(menuai: menuai, entry: FireServiceConfigEntry) -> bool:
    """Set up FireServiceRota from a config entry."""

    client = FireServiceRotaClient(menuai, entry)
    await client.setup()

    if client.token_refresh_failure:
        return False

    entry.async_on_unload(client.async_stop_listener)
    coordinator = FireServiceUpdateCoordinator(menuai, client, entry)

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    menuai: menuai, entry: FireServiceConfigEntry
) -> bool:
    """Unload FireServiceRota config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
