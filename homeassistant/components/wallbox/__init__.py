"""The Wallbox integration."""

from __future__ import annotations

from wallbox import Wallbox

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_PASSWORD, CONF_USERNAME, Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryAuthFailed

from .const import DOMAIN, UPDATE_INTERVAL
from .coordinator import InvalidAuth, WallboxCoordinator, async_validate_input

PLATFORMS = [
    Platform.LOCK,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up Wallbox from a config entry."""
    wallbox = Wallbox(
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        jwtTokenDrift=UPDATE_INTERVAL,
    )
    try:
        await async_validate_input(menuai, wallbox)
    except InvalidAuth as ex:
        raise ConfigEntryAuthFailed from ex

    wallbox_coordinator = WallboxCoordinator(menuai, entry, wallbox)
    await wallbox_coordinator.async_config_entry_first_refresh()

    menuai.data.setdefault(DOMAIN, {})[entry.entry_id] = wallbox_coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        menuai.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
