"""The Powerfox integration."""

from __future__ import annotations

import asyncio

from powerfox import Powerfox, PowerfoxConnectionError

from menuai.const import CONF_EMAIL, CONF_PASSWORD, Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers.aiohttp_client import async_get_clientsession

from .coordinator import PowerfoxConfigEntry, PowerfoxDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(menuai: menuai, entry: PowerfoxConfigEntry) -> bool:
    """Set up Powerfox from a config entry."""
    client = Powerfox(
        username=entry.data[CONF_EMAIL],
        password=entry.data[CONF_PASSWORD],
        session=async_get_clientsession(menuai),
    )

    try:
        devices = await client.all_devices()
    except PowerfoxConnectionError as err:
        await client.close()
        raise ConfigEntryNotReady from err

    coordinators: list[PowerfoxDataUpdateCoordinator] = [
        PowerfoxDataUpdateCoordinator(menuai, entry, client, device) for device in devices
    ]

    await asyncio.gather(
        *[
            coordinator.async_config_entry_first_refresh()
            for coordinator in coordinators
        ]
    )

    entry.runtime_data = coordinators

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(menuai: menuai, entry: PowerfoxConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
