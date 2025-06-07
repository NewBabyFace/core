"""The Steamist integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from aiosteamist import Steamist

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_HOST, Platform
from menuai.core import menuai
from menuai.helpers import config_validation as cv
from menuai.helpers.aiohttp_client import async_get_clientsession
from menuai.helpers.event import async_track_time_interval
from menuai.helpers.typing import ConfigType

from .const import DISCOVER_SCAN_TIMEOUT, DISCOVERY, DOMAIN
from .coordinator import SteamistDataUpdateCoordinator
from .discovery import (
    async_discover_device,
    async_discover_devices,
    async_get_discovery,
    async_trigger_discovery,
    async_update_entry_from_discovery,
)

PLATFORMS: list[str] = [Platform.SENSOR, Platform.SWITCH]
DISCOVERY_INTERVAL = timedelta(minutes=15)
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the steamist component."""
    domain_data = menuai.data.setdefault(DOMAIN, {})
    domain_data[DISCOVERY] = []

    async def _async_discovery(*_: Any) -> None:
        async_trigger_discovery(
            menuai, await async_discover_devices(menuai, DISCOVER_SCAN_TIMEOUT)
        )

    menuai.async_create_background_task(
        _async_discovery(), "steamist-discovery", eager_start=True
    )
    async_track_time_interval(menuai, _async_discovery, DISCOVERY_INTERVAL)
    return True


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up Steamist from a config entry."""
    host = entry.data[CONF_HOST]
    coordinator = SteamistDataUpdateCoordinator(
        menuai,
        entry,
        Steamist(host, async_get_clientsession(menuai)),
    )
    await coordinator.async_config_entry_first_refresh()
    if not async_get_discovery(menuai, host):
        if discovery := await async_discover_device(menuai, host):
            async_update_entry_from_discovery(menuai, entry, discovery)
    menuai.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        menuai.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
