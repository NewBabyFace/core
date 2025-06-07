"""The radiotherm component."""

from __future__ import annotations

from collections.abc import Coroutine
from typing import Any
from urllib.error import URLError

from radiotherm.validate import RadiothermTstatError

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_HOST, Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .coordinator import RadioThermUpdateCoordinator
from .data import async_get_init_data
from .util import async_set_time

PLATFORMS: list[Platform] = [Platform.CLIMATE, Platform.SWITCH]


async def _async_call_or_raise_not_ready[_T](
    coro: Coroutine[Any, Any, _T], host: str
) -> _T:
    """Call a coro or raise ConfigEntryNotReady."""
    try:
        return await coro
    except RadiothermTstatError as ex:
        msg = f"{host} was busy (invalid value returned): {ex}"
        raise ConfigEntryNotReady(msg) from ex
    except TimeoutError as ex:
        msg = f"{host} timed out waiting for a response: {ex}"
        raise ConfigEntryNotReady(msg) from ex
    except (OSError, URLError) as ex:
        msg = f"{host} connection error: {ex}"
        raise ConfigEntryNotReady(msg) from ex


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up Radio Thermostat from a config entry."""
    host = entry.data[CONF_HOST]
    init_coro = async_get_init_data(menuai, host)
    init_data = await _async_call_or_raise_not_ready(init_coro, host)
    coordinator = RadioThermUpdateCoordinator(menuai, entry, init_data)
    await coordinator.async_config_entry_first_refresh()

    # Only set the time if the thermostat is
    # not in hold mode since setting the time
    # clears the hold for some strange design
    # choice
    if not coordinator.data.tstat["hold"]:
        time_coro = async_set_time(menuai, init_data.tstat)
        await _async_call_or_raise_not_ready(time_coro, host)

    menuai.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def _async_update_listener(menuai: menuai, entry: ConfigEntry) -> None:
    """Handle options update."""
    await menuai.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        menuai.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
