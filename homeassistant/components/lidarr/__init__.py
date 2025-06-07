"""The Lidarr component."""

from __future__ import annotations

from dataclasses import fields

from aiopyarr.lidarr_client import LidarrClient
from aiopyarr.models.host_configuration import PyArrHostConfiguration

from menuai.const import CONF_API_KEY, CONF_URL, CONF_VERIFY_SSL, Platform
from menuai.core import menuai
from menuai.helpers import device_registry as dr
from menuai.helpers.aiohttp_client import async_get_clientsession
from menuai.helpers.device_registry import DeviceEntryType

from .const import DEFAULT_NAME, DOMAIN
from .coordinator import (
    AlbumsDataUpdateCoordinator,
    DiskSpaceDataUpdateCoordinator,
    LidarrConfigEntry,
    LidarrData,
    QueueDataUpdateCoordinator,
    StatusDataUpdateCoordinator,
    WantedDataUpdateCoordinator,
)

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(menuai: menuai, entry: LidarrConfigEntry) -> bool:
    """Set up Lidarr from a config entry."""
    host_configuration = PyArrHostConfiguration(
        api_token=entry.data[CONF_API_KEY],
        verify_ssl=entry.data[CONF_VERIFY_SSL],
        url=entry.data[CONF_URL],
    )
    lidarr = LidarrClient(
        host_configuration=host_configuration,
        session=async_get_clientsession(menuai, host_configuration.verify_ssl),
        request_timeout=60,
    )
    data = LidarrData(
        disk_space=DiskSpaceDataUpdateCoordinator(
            menuai, entry, host_configuration, lidarr
        ),
        queue=QueueDataUpdateCoordinator(menuai, entry, host_configuration, lidarr),
        status=StatusDataUpdateCoordinator(menuai, entry, host_configuration, lidarr),
        wanted=WantedDataUpdateCoordinator(menuai, entry, host_configuration, lidarr),
        albums=AlbumsDataUpdateCoordinator(menuai, entry, host_configuration, lidarr),
    )
    for field in fields(data):
        coordinator = getattr(data, field.name)
        await coordinator.async_config_entry_first_refresh()
    device_registry = dr.async_get(menuai)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        configuration_url=entry.data[CONF_URL],
        entry_type=DeviceEntryType.SERVICE,
        identifiers={(DOMAIN, entry.entry_id)},
        manufacturer=DEFAULT_NAME,
        sw_version=data.status.data,
    )
    entry.runtime_data = data
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: LidarrConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
