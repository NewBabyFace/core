"""Refoss devices platform loader."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers.event import async_track_time_interval

from .bridge import DiscoveryService
from .const import COORDINATORS, DATA_DISCOVERY_SERVICE, DISCOVERY_SCAN_INTERVAL, DOMAIN
from .util import refoss_discovery_server

PLATFORMS: Final = [
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up Refoss from a config entry."""
    menuai.data.setdefault(DOMAIN, {})
    discover = await refoss_discovery_server(menuai)
    refoss_discovery = DiscoveryService(menuai, entry, discover)
    menuai.data[DOMAIN][DATA_DISCOVERY_SERVICE] = refoss_discovery

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def _async_scan_update(_=None):
        await refoss_discovery.discovery.broadcast_msg()

    await _async_scan_update()

    entry.async_on_unload(
        async_track_time_interval(
            menuai, _async_scan_update, timedelta(seconds=DISCOVERY_SCAN_INTERVAL)
        )
    )

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if menuai.data[DOMAIN].get(DATA_DISCOVERY_SERVICE) is not None:
        refoss_discovery: DiscoveryService = menuai.data[DOMAIN][DATA_DISCOVERY_SERVICE]
        refoss_discovery.discovery.clean_up()
        menuai.data[DOMAIN].pop(DATA_DISCOVERY_SERVICE)

    unload_ok = await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        menuai.data[DOMAIN].pop(COORDINATORS)

    return unload_ok
