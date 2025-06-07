"""The Garages Amsterdam integration."""

from __future__ import annotations

from odp_amsterdam import ODPAmsterdam

from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers.aiohttp_client import async_get_clientsession

from .coordinator import (
    GaragesAmsterdamConfigEntry,
    GaragesAmsterdamDataUpdateCoordinator,
)

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]


async def async_setup_entry(
    menuai: menuai, entry: GaragesAmsterdamConfigEntry
) -> bool:
    """Set up Garages Amsterdam from a config entry."""
    client = ODPAmsterdam(session=async_get_clientsession(menuai))
    coordinator = GaragesAmsterdamDataUpdateCoordinator(menuai, entry, client)

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    menuai: menuai, entry: GaragesAmsterdamConfigEntry
) -> bool:
    """Unload Garages Amsterdam config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
