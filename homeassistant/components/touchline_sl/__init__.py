"""The Roth Touchline SL integration."""

from __future__ import annotations

import asyncio

from pytouchlinesl import TouchlineSL

from menuai.const import CONF_PASSWORD, CONF_USERNAME, Platform
from menuai.core import menuai
from menuai.helpers import device_registry as dr

from .const import DOMAIN
from .coordinator import TouchlineSLConfigEntry, TouchlineSLModuleCoordinator

PLATFORMS: list[Platform] = [Platform.CLIMATE]


async def async_setup_entry(menuai: menuai, entry: TouchlineSLConfigEntry) -> bool:
    """Set up Roth Touchline SL from a config entry."""
    account = TouchlineSL(
        username=entry.data[CONF_USERNAME], password=entry.data[CONF_PASSWORD]
    )

    coordinators: list[TouchlineSLModuleCoordinator] = [
        TouchlineSLModuleCoordinator(menuai, entry, module)
        for module in await account.modules()
    ]

    await asyncio.gather(
        *[
            coordinator.async_config_entry_first_refresh()
            for coordinator in coordinators
        ]
    )

    device_registry = dr.async_get(menuai)

    # Create a new Device for each coorodinator to represent each module
    for c in coordinators:
        module = c.data.module
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, module.id)},
            name=module.name,
            manufacturer="Roth",
            model=module.type,
            sw_version=module.version,
        )

    entry.runtime_data = coordinators
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    menuai: menuai, entry: TouchlineSLConfigEntry
) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
