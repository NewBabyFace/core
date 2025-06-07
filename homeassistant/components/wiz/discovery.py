"""The wiz integration discovery."""

from __future__ import annotations

import asyncio
from dataclasses import asdict
import logging

from pywizlight.discovery import DiscoveredBulb, find_wizlights

from menuai import config_entries
from menuai.components import network
from menuai.core import menuai, callback
from menuai.helpers import discovery_flow

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_discover_devices(
    menuai: menuai, timeout: int
) -> list[DiscoveredBulb]:
    """Discover wiz devices."""
    broadcast_addrs = await network.async_get_ipv4_broadcast_addresses(menuai)
    targets = [str(address) for address in broadcast_addrs]
    combined_discoveries: dict[str, DiscoveredBulb] = {}
    for idx, discovered in enumerate(
        await asyncio.gather(
            *[find_wizlights(timeout, address) for address in targets],
            return_exceptions=True,
        )
    ):
        if isinstance(discovered, Exception):
            _LOGGER.debug("Scanning %s failed with error: %s", targets[idx], discovered)
            continue
        if isinstance(discovered, BaseException):
            raise discovered from None
        for device in discovered:
            assert isinstance(device, DiscoveredBulb)
            combined_discoveries[device.ip_address] = device

    return list(combined_discoveries.values())


@callback
def async_trigger_discovery(
    menuai: menuai,
    discovered_devices: list[DiscoveredBulb],
) -> None:
    """Trigger config flows for discovered devices."""
    for device in discovered_devices:
        discovery_flow.async_create_flow(
            menuai,
            DOMAIN,
            context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
            data=asdict(device),
        )
