"""The Broadlink integration."""

from __future__ import annotations

from dataclasses import dataclass, field

from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers import config_validation as cv
from menuai.helpers.typing import ConfigType

from .const import DOMAIN
from .device import BroadlinkDevice
from .heartbeat import BroadlinkHeartbeat

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


@dataclass
class BroadlinkData:
    """Class for sharing data within the Broadlink integration."""

    devices: dict[str, BroadlinkDevice] = field(default_factory=dict)
    platforms: dict = field(default_factory=dict)
    heartbeat: BroadlinkHeartbeat | None = None


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the Broadlink integration."""
    menuai.data[DOMAIN] = BroadlinkData()
    return True


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up a Broadlink device from a config entry."""
    data: BroadlinkData = menuai.data[DOMAIN]

    device = BroadlinkDevice(menuai, entry)
    if not await device.async_setup():
        return False
    if data.heartbeat is None:
        data.heartbeat = BroadlinkHeartbeat(menuai)
        menuai.async_create_task(data.heartbeat.async_setup())
    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    data: BroadlinkData = menuai.data[DOMAIN]

    device = data.devices.pop(entry.entry_id)
    result = await device.async_unload()

    if data.heartbeat and not data.devices:
        await data.heartbeat.async_unload()
        data.heartbeat = None

    return result
