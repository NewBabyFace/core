"""The lifx integration discovery."""

from __future__ import annotations

import asyncio
from collections.abc import Collection, Iterable

from aiolifx.aiolifx import LifxDiscovery, Light, ScanManager

from menuai import config_entries
from menuai.components import network
from menuai.const import CONF_HOST
from menuai.core import menuai, callback
from menuai.helpers import discovery_flow

from .const import CONF_SERIAL, DOMAIN

DEFAULT_TIMEOUT = 8.5


async def async_discover_devices(menuai: menuai) -> Collection[Light]:
    """Discover lifx devices."""
    all_lights: dict[str, Light] = {}
    broadcast_addrs = await network.async_get_ipv4_broadcast_addresses(menuai)
    discoveries = []
    for address in broadcast_addrs:
        manager = ScanManager(str(address))
        lifx_discovery = LifxDiscovery(menuai.loop, manager, broadcast_ip=str(address))
        discoveries.append(lifx_discovery)
        lifx_discovery.start()

    await asyncio.sleep(DEFAULT_TIMEOUT)
    for discovery in discoveries:
        all_lights.update(discovery.lights)
        discovery.cleanup()

    return all_lights.values()


@callback
def async_init_discovery_flow(menuai: menuai, host: str, serial: str) -> None:
    """Start discovery of devices."""
    discovery_flow.async_create_flow(
        menuai,
        DOMAIN,
        context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
        data={CONF_HOST: host, CONF_SERIAL: serial},
    )


@callback
def async_trigger_discovery(
    menuai: menuai,
    discovered_devices: Iterable[Light],
) -> None:
    """Trigger config flows for discovered devices."""
    for device in discovered_devices:
        # device.mac_addr is not the mac_address, its the serial number
        async_init_discovery_flow(menuai, device.ip_addr, device.mac_addr)
