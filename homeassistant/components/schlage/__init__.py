"""The Schlage integration."""

from __future__ import annotations

from pycognito.exceptions import WarrantException
import pyschlage

from menuai.const import CONF_PASSWORD, CONF_USERNAME, Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryAuthFailed

from .coordinator import SchlageConfigEntry, SchlageDataUpdateCoordinator

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.LOCK,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(menuai: menuai, entry: SchlageConfigEntry) -> bool:
    """Set up Schlage from a config entry."""
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    try:
        auth = await menuai.async_add_executor_job(pyschlage.Auth, username, password)
    except WarrantException as ex:
        raise ConfigEntryAuthFailed from ex

    coordinator = SchlageDataUpdateCoordinator(
        menuai, entry, username, pyschlage.Schlage(auth)
    )
    entry.runtime_data = coordinator
    await coordinator.async_config_entry_first_refresh()
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(menuai: menuai, entry: SchlageConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
