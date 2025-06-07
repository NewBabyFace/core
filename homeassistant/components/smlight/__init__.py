"""SMLIGHT SLZB Zigbee device integration."""

from __future__ import annotations

from pysmlight import Api2

from menuai.const import CONF_HOST, Platform
from menuai.core import menuai
from menuai.helpers.aiohttp_client import async_get_clientsession

from .coordinator import (
    SmConfigEntry,
    SmDataUpdateCoordinator,
    SmFirmwareUpdateCoordinator,
    SmlightData,
)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.UPDATE,
]


async def async_setup_entry(menuai: menuai, entry: SmConfigEntry) -> bool:
    """Set up SMLIGHT Zigbee from a config entry."""
    client = Api2(host=entry.data[CONF_HOST], session=async_get_clientsession(menuai))

    data_coordinator = SmDataUpdateCoordinator(menuai, entry, client)
    firmware_coordinator = SmFirmwareUpdateCoordinator(menuai, entry, client)

    await data_coordinator.async_config_entry_first_refresh()
    await firmware_coordinator.async_config_entry_first_refresh()

    if data_coordinator.data.info.legacy_api < 2:
        entry.async_create_background_task(
            menuai, client.sse.client(), "smlight-sse-client"
        )

    entry.runtime_data = SmlightData(
        data=data_coordinator, firmware=firmware_coordinator
    )

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(menuai: menuai, entry: SmConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
