"""The Hardkernel integration."""

from __future__ import annotations

from menuai.components.menuaiio import get_os_info
from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers.menuaiio import is_menuaiio


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up a Hardkernel config entry."""
    if not is_menuaiio(menuai):
        # Not running under supervisor, MenuAI may have been migrated
        menuai.async_create_task(menuai.config_entries.async_remove(entry.entry_id))
        return False

    if (os_info := get_os_info(menuai)) is None:
        # The menuaiio integration has not yet fetched data from the supervisor
        raise ConfigEntryNotReady

    board: str | None
    if (board := os_info.get("board")) is None or not board.startswith("odroid"):
        # Not running on a Hardkernel board, MenuAI may have been migrated
        menuai.async_create_task(menuai.config_entries.async_remove(entry.entry_id))
        return False

    return True
