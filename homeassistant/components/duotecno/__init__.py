"""The duotecno integration."""

from __future__ import annotations

from duotecno.controller import PyDuotecno
from duotecno.exceptions import InvalidPassword, LoadFailure

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.COVER,
    Platform.LIGHT,
    Platform.SWITCH,
]


type DuotecnoConfigEntry = ConfigEntry[PyDuotecno]


async def async_setup_entry(menuai: menuai, entry: DuotecnoConfigEntry) -> bool:
    """Set up duotecno from a config entry."""

    controller = PyDuotecno()
    try:
        await controller.connect(
            entry.data[CONF_HOST], entry.data[CONF_PORT], entry.data[CONF_PASSWORD]
        )
    except (OSError, InvalidPassword, LoadFailure) as err:
        raise ConfigEntryNotReady from err

    entry.runtime_data = controller
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(menuai: menuai, entry: DuotecnoConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
