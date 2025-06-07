"""The Dune HD component."""

from __future__ import annotations

from typing import Final

from pdunehd import DuneHDPlayer

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_HOST, Platform
from menuai.core import menuai

PLATFORMS: Final[list[Platform]] = [Platform.MEDIA_PLAYER]


type DuneHDConfigEntry = ConfigEntry[DuneHDPlayer]


async def async_setup_entry(menuai: menuai, entry: DuneHDConfigEntry) -> bool:
    """Set up a config entry."""
    entry.runtime_data = DuneHDPlayer(entry.data[CONF_HOST])

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: DuneHDConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
