"""The Steamist integration discovery."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from discovery30303 import AIODiscovery30303, Device30303

from menuai import config_entries
from menuai.components import network
from menuai.const import CONF_MODEL, CONF_NAME
from menuai.core import menuai, callback
from menuai.helpers import device_registry as dr, discovery_flow
from menuai.util.network import is_ip_address

from .const import DISCOVER_SCAN_TIMEOUT, DISCOVERY, DOMAIN

_LOGGER = logging.getLogger(__name__)


MODEL_450_HOSTNAME_PREFIX = "MY450-"
MODEL_550_HOSTNAME_PREFIX = "MY550-"


@callback
def async_is_steamist_device(device: Device30303) -> bool:
    """Check if a 30303 discovery is a steamist device."""
    return device.hostname.startswith(
        MODEL_450_HOSTNAME_PREFIX
    ) or device.hostname.startswith(MODEL_550_HOSTNAME_PREFIX)


@callback
def async_update_entry_from_discovery(
    menuai: menuai,
    entry: config_entries.ConfigEntry,
    device: Device30303,
) -> bool:
    """Update a config entry from a discovery."""
    data_updates: dict[str, Any] = {}
    updates: dict[str, Any] = {}
    if not entry.unique_id:
        updates["unique_id"] = dr.format_mac(device.mac)
    if not entry.data.get(CONF_NAME) or is_ip_address(entry.data[CONF_NAME]):
        updates["title"] = data_updates[CONF_NAME] = device.name
    if not entry.data.get(CONF_MODEL) and "-" in device.hostname:
        data_updates[CONF_MODEL] = device.hostname.split("-", maxsplit=1)[0]
    if data_updates:
        updates["data"] = {**entry.data, **data_updates}
    if updates:
        return menuai.config_entries.async_update_entry(entry, **updates)
    return False


async def async_discover_devices(
    menuai: menuai, timeout: int, address: str | None = None
) -> list[Device30303]:
    """Discover devices."""
    if address:
        targets = [address]
    else:
        targets = [
            str(broadcast_address)
            for broadcast_address in await network.async_get_ipv4_broadcast_addresses(
                menuai
            )
        ]

    scanner = AIODiscovery30303()
    for idx, discovered in enumerate(
        await asyncio.gather(
            *[
                scanner.async_scan(timeout=timeout, address=target_address)
                for target_address in targets
            ],
            return_exceptions=True,
        )
    ):
        if isinstance(discovered, Exception):
            _LOGGER.debug("Scanning %s failed with error: %s", targets[idx], discovered)
            continue

    _LOGGER.debug("Found devices: %s", scanner.found_devices)
    if not address:
        return [
            device
            for device in scanner.found_devices
            if async_is_steamist_device(device)
        ]

    return [device for device in scanner.found_devices if device.ipaddress == address]


@callback
def async_find_discovery_by_ip(
    discoveries: list[Device30303], host: str
) -> Device30303 | None:
    """Search a list of discoveries for one with a matching ip."""
    for discovery in discoveries:
        if discovery.ipaddress == host:
            return discovery
    return None


async def async_discover_device(menuai: menuai, host: str) -> Device30303 | None:
    """Direct discovery to a single ip instead of broadcast."""
    return async_find_discovery_by_ip(
        await async_discover_devices(menuai, DISCOVER_SCAN_TIMEOUT, host), host
    )


@callback
def async_get_discovery(menuai: menuai, host: str) -> Device30303 | None:
    """Check if a device was already discovered via a broadcast discovery."""
    discoveries: list[Device30303] = menuai.data[DOMAIN][DISCOVERY]
    return async_find_discovery_by_ip(discoveries, host)


@callback
def async_trigger_discovery(
    menuai: menuai,
    discovered_devices: list[Device30303],
) -> None:
    """Trigger config flows for discovered devices."""
    for device in discovered_devices:
        discovery_flow.async_create_flow(
            menuai,
            DOMAIN,
            context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
            data={
                "ipaddress": device.ipaddress,
                "name": device.name,
                "mac": device.mac,
                "hostname": device.hostname,
            },
        )
