"""The awair component."""

from __future__ import annotations

from menuai.const import CONF_HOST, Platform
from menuai.core import menuai
from menuai.helpers.aiohttp_client import async_get_clientsession

from .coordinator import (
    AwairCloudDataUpdateCoordinator,
    AwairConfigEntry,
    AwairDataUpdateCoordinator,
    AwairLocalDataUpdateCoordinator,
)

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(
    menuai: menuai, config_entry: AwairConfigEntry
) -> bool:
    """Set up Awair integration from a config entry."""
    session = async_get_clientsession(menuai)

    coordinator: AwairDataUpdateCoordinator

    if CONF_HOST in config_entry.data:
        coordinator = AwairLocalDataUpdateCoordinator(menuai, config_entry, session)
        config_entry.async_on_unload(
            config_entry.add_update_listener(_async_update_listener)
        )
    else:
        coordinator = AwairCloudDataUpdateCoordinator(menuai, config_entry, session)

    await coordinator.async_config_entry_first_refresh()

    config_entry.runtime_data = coordinator

    await menuai.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    return True


async def _async_update_listener(menuai: menuai, entry: AwairConfigEntry) -> None:
    """Handle options update."""
    if entry.title != entry.runtime_data.title:
        await menuai.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(
    menuai: menuai, config_entry: AwairConfigEntry
) -> bool:
    """Unload Awair configuration."""
    return await menuai.config_entries.async_unload_platforms(config_entry, PLATFORMS)
