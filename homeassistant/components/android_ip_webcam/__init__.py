"""The Android IP Webcam integration."""

from __future__ import annotations

from pydroid_ipcam import PyDroidIPCam

from menuai.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
    Platform,
)
from menuai.core import menuai
from menuai.helpers.aiohttp_client import async_get_clientsession

from .coordinator import AndroidIPCamConfigEntry, AndroidIPCamDataUpdateCoordinator

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.CAMERA,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(
    menuai: menuai, entry: AndroidIPCamConfigEntry
) -> bool:
    """Set up Android IP Webcam from a config entry."""
    websession = async_get_clientsession(menuai)
    cam = PyDroidIPCam(
        websession,
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
        username=entry.data.get(CONF_USERNAME),
        password=entry.data.get(CONF_PASSWORD),
        ssl=False,
    )
    coordinator = AndroidIPCamDataUpdateCoordinator(menuai, entry, cam)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    menuai: menuai, entry: AndroidIPCamConfigEntry
) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
