"""Support for monitoring an SABnzbd NZB client."""

from __future__ import annotations

import logging

from menuai.const import Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady

from .coordinator import SabnzbdConfigEntry, SabnzbdUpdateCoordinator
from .helpers import get_client

PLATFORMS = [Platform.BINARY_SENSOR, Platform.BUTTON, Platform.NUMBER, Platform.SENSOR]
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(menuai: menuai, entry: SabnzbdConfigEntry) -> bool:
    """Set up the SabNzbd Component."""

    sab_api = await get_client(menuai, entry.data)
    if not sab_api:
        raise ConfigEntryNotReady

    coordinator = SabnzbdUpdateCoordinator(menuai, entry, sab_api)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: SabnzbdConfigEntry) -> bool:
    """Unload a Sabnzbd config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
