"""Config flow for Fjäråskupan integration."""

from __future__ import annotations

from fjaraskupan import device_filter

from menuai.components.bluetooth import async_discovered_service_info
from menuai.core import menuai
from menuai.helpers.config_entry_flow import register_discovery_flow

from .const import DOMAIN


async def _async_has_devices(menuai: menuai) -> bool:
    """Return if there are devices that can be discovered."""

    service_infos = async_discovered_service_info(menuai)

    for service_info in service_infos:
        if device_filter(service_info.device, service_info.advertisement):
            return True

    return False


register_discovery_flow(DOMAIN, "Fjäråskupan", _async_has_devices)
