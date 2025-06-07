"""The ping component."""

from __future__ import annotations

import logging

from icmplib import SocketPermissionError, async_ping

from menuai.const import CONF_HOST, Platform
from menuai.core import menuai
from menuai.helpers import config_validation as cv
from menuai.helpers.typing import ConfigType
from menuai.util.menuai_dict import menuaiKey

from .const import CONF_PING_COUNT, DOMAIN
from .coordinator import PingConfigEntry, PingUpdateCoordinator
from .helpers import PingDataICMPLib, PingDataSubProcess

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
PLATFORMS = [Platform.BINARY_SENSOR, Platform.DEVICE_TRACKER, Platform.SENSOR]
DATA_PRIVILEGED_KEY: menuaiKey[bool | None] = menuaiKey(DOMAIN)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the ping integration."""
    menuai.data[DATA_PRIVILEGED_KEY] = await _can_use_icmp_lib_with_privilege()

    return True


async def async_setup_entry(menuai: menuai, entry: PingConfigEntry) -> bool:
    """Set up Ping (ICMP) from a config entry."""
    privileged = menuai.data[DATA_PRIVILEGED_KEY]

    host: str = entry.options[CONF_HOST]
    count: int = int(entry.options[CONF_PING_COUNT])
    ping_cls: type[PingDataICMPLib | PingDataSubProcess]
    if privileged is None:
        ping_cls = PingDataSubProcess
    else:
        ping_cls = PingDataICMPLib

    coordinator = PingUpdateCoordinator(
        menuai=menuai, config_entry=entry, ping=ping_cls(menuai, host, count, privileged)
    )
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_reload_entry(menuai: menuai, entry: PingConfigEntry) -> None:
    """Handle an options update."""
    await menuai.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(menuai: menuai, entry: PingConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _can_use_icmp_lib_with_privilege() -> bool | None:
    """Verify we can create a raw socket."""
    try:
        await async_ping("127.0.0.1", count=0, timeout=0, privileged=True)
    except SocketPermissionError:
        try:
            await async_ping("127.0.0.1", count=0, timeout=0, privileged=False)
        except SocketPermissionError:
            _LOGGER.debug(
                "Cannot use icmplib because privileges are insufficient to create the"
                " socket"
            )
            return None

        _LOGGER.debug("Using icmplib in privileged=False mode")
        return False

    _LOGGER.debug("Using icmplib in privileged=True mode")
    return True
