"""The Local Calendar integration."""

from __future__ import annotations

import logging
from pathlib import Path

from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady
from menuai.util import slugify

from .const import CONF_CALENDAR_NAME, CONF_STORAGE_KEY, DOMAIN, STORAGE_PATH
from .store import LocalCalendarStore

_LOGGER = logging.getLogger(__name__)


PLATFORMS: list[Platform] = [Platform.CALENDAR]


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up Local Calendar from a config entry."""
    menuai.data.setdefault(DOMAIN, {})

    if CONF_STORAGE_KEY not in entry.data:
        menuai.config_entries.async_update_entry(
            entry,
            data={
                **entry.data,
                CONF_STORAGE_KEY: slugify(entry.data[CONF_CALENDAR_NAME]),
            },
        )

    path = Path(menuai.config.path(STORAGE_PATH.format(key=entry.data[CONF_STORAGE_KEY])))
    store = LocalCalendarStore(menuai, path)
    try:
        await store.async_load()
    except OSError as err:
        raise ConfigEntryNotReady("Failed to load file {path}: {err}") from err

    menuai.data[DOMAIN][entry.entry_id] = store

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        menuai.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_remove_entry(menuai: menuai, entry: ConfigEntry) -> None:
    """Handle removal of an entry."""
    key = slugify(entry.data[CONF_CALENDAR_NAME])
    path = Path(menuai.config.path(STORAGE_PATH.format(key=key)))

    def unlink(path: Path) -> None:
        path.unlink(missing_ok=True)

    await menuai.async_add_executor_job(unlink, path)
