"""The Wyoming integration."""

from __future__ import annotations

import logging

from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers import config_validation as cv, device_registry as dr
from menuai.helpers.typing import ConfigType

from .const import ATTR_SPEAKER, DOMAIN
from .data import WyomingService
from .devices import SatelliteDevice
from .models import DomainDataItem
from .websocket_api import async_register_websocket_api

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)

SATELLITE_PLATFORMS = [
    Platform.ASSIST_SATELLITE,
    Platform.BINARY_SENSOR,
    Platform.SELECT,
    Platform.SWITCH,
    Platform.NUMBER,
]

__all__ = [
    "ATTR_SPEAKER",
    "DOMAIN",
    "async_setup",
    "async_setup_entry",
    "async_unload_entry",
]


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the Wyoming integration."""
    async_register_websocket_api(menuai)

    return True


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Load Wyoming."""
    service = await WyomingService.create(entry.data["host"], entry.data["port"])

    if service is None:
        raise ConfigEntryNotReady("Unable to connect")

    item = DomainDataItem(service=service)
    menuai.data.setdefault(DOMAIN, {})[entry.entry_id] = item

    await menuai.config_entries.async_forward_entry_setups(entry, service.platforms)
    entry.async_on_unload(entry.add_update_listener(update_listener))

    if (satellite_info := service.info.satellite) is not None:
        # Create satellite device
        dev_reg = dr.async_get(menuai)

        # Use config entry id since only one satellite per entry is supported
        satellite_id = entry.entry_id
        device = dev_reg.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, satellite_id)},
            name=satellite_info.name,
            suggested_area=satellite_info.area,
        )

        item.device = SatelliteDevice(
            satellite_id=satellite_id,
            device_id=device.id,
        )

        # Set up satellite entity, sensors, switches, etc.
        await menuai.config_entries.async_forward_entry_setups(entry, SATELLITE_PLATFORMS)

    return True


async def update_listener(menuai: menuai, entry: ConfigEntry):
    """Handle options update."""
    await menuai.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload Wyoming."""
    item: DomainDataItem = menuai.data[DOMAIN][entry.entry_id]

    platforms = list(item.service.platforms)
    if item.device is not None:
        platforms += SATELLITE_PLATFORMS

    unload_ok = await menuai.config_entries.async_unload_platforms(entry, platforms)
    if unload_ok:
        del menuai.data[DOMAIN][entry.entry_id]

    return unload_ok
