"""iAlarm integration."""

from __future__ import annotations

import asyncio

from pyialarm import IAlarm

from menuai.const import CONF_HOST, CONF_PORT, Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady

from .coordinator import IAlarmConfigEntry, IAlarmDataUpdateCoordinator

PLATFORMS = [Platform.ALARM_CONTROL_PANEL]


async def async_setup_entry(menuai: menuai, entry: IAlarmConfigEntry) -> bool:
    """Set up iAlarm config."""
    host: str = entry.data[CONF_HOST]
    port: int = entry.data[CONF_PORT]
    ialarm = IAlarm(host, port)

    try:
        async with asyncio.timeout(10):
            mac = await menuai.async_add_executor_job(ialarm.get_mac)
    except (TimeoutError, ConnectionError) as ex:
        raise ConfigEntryNotReady from ex

    coordinator = IAlarmDataUpdateCoordinator(menuai, entry, ialarm, mac)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: IAlarmConfigEntry) -> bool:
    """Unload iAlarm config."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
