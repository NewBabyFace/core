"""The Thread integration."""

from __future__ import annotations

from menuai.config_entries import SOURCE_IMPORT, ConfigEntry
from menuai.core import menuai
from menuai.helpers import config_validation as cv
from menuai.helpers.typing import ConfigType

from .const import DOMAIN
from .dataset_store import (
    DatasetEntry,
    async_add_dataset,
    async_get_dataset,
    async_get_preferred_dataset,
)
from .websocket_api import async_setup as async_setup_ws_api

__all__ = [
    "DOMAIN",
    "DatasetEntry",
    "async_add_dataset",
    "async_get_dataset",
    "async_get_preferred_dataset",
]

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the Thread integration."""
    if not menuai.config_entries.async_entries(DOMAIN):
        menuai.async_create_task(
            menuai.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_IMPORT}
            )
        )
    async_setup_ws_api(menuai)
    menuai.data[DOMAIN] = {}
    return True


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up a config entry."""

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return True
