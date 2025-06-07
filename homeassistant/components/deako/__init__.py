"""The deako integration."""

from __future__ import annotations

import logging

from pydeako import Deako, DeakoDiscoverer, FindDevicesError

from menuai.components import zeroconf
from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady

_LOGGER: logging.Logger = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.LIGHT]

type DeakoConfigEntry = ConfigEntry[Deako]


async def async_setup_entry(menuai: menuai, entry: DeakoConfigEntry) -> bool:
    """Set up deako."""
    _zc = await zeroconf.async_get_instance(menuai)
    discoverer = DeakoDiscoverer(_zc)

    connection = Deako(discoverer.get_address)

    await connection.connect()
    try:
        await connection.find_devices()
    except FindDevicesError as exc:
        _LOGGER.warning("Error finding devices: %s", exc)
        await connection.disconnect()
        raise ConfigEntryNotReady(exc) from exc

    # If deako devices are advertising on mdns, we should be able to get at least one device
    devices = connection.get_devices()
    if len(devices) == 0:
        await connection.disconnect()
        raise ConfigEntryNotReady(devices)

    entry.runtime_data = connection

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: DeakoConfigEntry) -> bool:
    """Unload a config entry."""
    await entry.runtime_data.disconnect()

    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
