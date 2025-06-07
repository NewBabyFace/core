"""The Goal Zero Yeti integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from goalzero import Yeti, exceptions

from menuai.const import CONF_HOST, Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers.aiohttp_client import async_get_clientsession
from menuai.helpers.device_registry import format_mac

from .coordinator import GoalZeroConfigEntry, GoalZeroDataUpdateCoordinator

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR, Platform.SWITCH]


async def async_setup_entry(menuai: menuai, entry: GoalZeroConfigEntry) -> bool:
    """Set up Goal Zero Yeti from a config entry."""

    mac = entry.unique_id

    if TYPE_CHECKING:
        assert mac is not None

    if (formatted_mac := format_mac(mac)) != mac:
        # The DHCP discovery path did not format the MAC address
        # so we need to update the config entry if it's different
        menuai.config_entries.async_update_entry(entry, unique_id=formatted_mac)

    api = Yeti(entry.data[CONF_HOST], async_get_clientsession(menuai))
    try:
        await api.init_connect()
    except exceptions.ConnectError as ex:
        raise ConfigEntryNotReady(f"Failed to connect to device: {ex}") from ex

    entry.runtime_data = GoalZeroDataUpdateCoordinator(menuai, entry, api)
    await entry.runtime_data.async_config_entry_first_refresh()
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: GoalZeroConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
