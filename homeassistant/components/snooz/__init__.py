"""The Snooz component."""

from __future__ import annotations

import logging

from pysnooz.device import SnoozDevice

from menuai.components.bluetooth import async_ble_device_from_address
from menuai.config_entries import ConfigEntry
from menuai.const import CONF_ADDRESS, CONF_TOKEN
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady

from .const import DOMAIN, PLATFORMS
from .models import SnoozConfigurationData


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up Snooz device from a config entry."""
    address: str = entry.data[CONF_ADDRESS]
    token: str = entry.data[CONF_TOKEN]

    # transitions info logs are verbose. Only enable warnings
    logging.getLogger("transitions.core").setLevel(logging.WARNING)

    if not (ble_device := async_ble_device_from_address(menuai, address)):
        raise ConfigEntryNotReady(
            f"Could not find Snooz with address {address}. Try power cycling the device"
        )

    device = SnoozDevice(ble_device, token)

    menuai.data.setdefault(DOMAIN, {})[entry.entry_id] = SnoozConfigurationData(
        ble_device, device, entry.title
    )

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(menuai: menuai, entry: ConfigEntry) -> None:
    """Handle options update."""
    data: SnoozConfigurationData = menuai.data[DOMAIN][entry.entry_id]
    if entry.title != data.title:
        await menuai.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        data: SnoozConfigurationData = menuai.data[DOMAIN][entry.entry_id]

        # also called by fan entities, but do it here too for good measure
        await data.device.async_disconnect()

        menuai.data[DOMAIN].pop(entry.entry_id)

        if not menuai.config_entries.async_entries(DOMAIN):
            menuai.data.pop(DOMAIN)

    return unload_ok
