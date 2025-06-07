"""The Gree Climate integration."""

from __future__ import annotations

from datetime import timedelta
import logging

from menuai.components.network import async_get_ipv4_broadcast_addresses
from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers.event import async_track_time_interval

from .const import DISCOVERY_SCAN_INTERVAL
from .coordinator import DiscoveryService, GreeConfigEntry, GreeRuntimeData

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.CLIMATE, Platform.SWITCH]


async def async_setup_entry(menuai: menuai, entry: GreeConfigEntry) -> bool:
    """Set up Gree Climate from a config entry."""
    gree_discovery = DiscoveryService(menuai, entry)
    entry.runtime_data = GreeRuntimeData(
        discovery_service=gree_discovery, coordinators=[]
    )

    async def _async_scan_update(_=None):
        bcast_addr = list(await async_get_ipv4_broadcast_addresses(menuai))
        await gree_discovery.discovery.scan(0, bcast_ifaces=bcast_addr)

    _LOGGER.debug("Scanning network for Gree devices")
    await _async_scan_update()

    entry.async_on_unload(
        async_track_time_interval(
            menuai, _async_scan_update, timedelta(seconds=DISCOVERY_SCAN_INTERVAL)
        )
    )

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: GreeConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
