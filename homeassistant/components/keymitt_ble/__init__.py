"""Integration to integrate Keymitt BLE devices with MenuAI."""

from __future__ import annotations

import logging

from microbot import MicroBotApiClient

from menuai.components import bluetooth
from menuai.config_entries import ConfigEntry
from menuai.const import CONF_ACCESS_TOKEN, CONF_ADDRESS, Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .coordinator import MicroBotDataUpdateCoordinator

_LOGGER: logging.Logger = logging.getLogger(__package__)
PLATFORMS: list[str] = [Platform.SWITCH]


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""
    menuai.data.setdefault(DOMAIN, {})
    token: str = entry.data[CONF_ACCESS_TOKEN]
    bdaddr: str = entry.data[CONF_ADDRESS]
    ble_device = bluetooth.async_ble_device_from_address(menuai, bdaddr)
    if not ble_device:
        raise ConfigEntryNotReady(f"Could not find MicroBot with address {bdaddr}")
    client = MicroBotApiClient(
        device=ble_device,
        token=token,
    )
    coordinator = MicroBotDataUpdateCoordinator(
        menuai, client=client, ble_device=ble_device
    )

    menuai.data[DOMAIN][entry.entry_id] = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(coordinator.async_start())

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        menuai.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
