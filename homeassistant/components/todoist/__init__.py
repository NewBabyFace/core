"""The todoist integration."""

import datetime
import logging

from todoist_api_python.api_async import TodoistAPIAsync

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_TOKEN, Platform
from menuai.core import menuai

from .const import DOMAIN
from .coordinator import TodoistCoordinator

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = datetime.timedelta(minutes=1)


PLATFORMS: list[Platform] = [Platform.CALENDAR, Platform.TODO]


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up todoist from a config entry."""

    token = entry.data[CONF_TOKEN]
    api = TodoistAPIAsync(token)
    coordinator = TodoistCoordinator(menuai, _LOGGER, entry, SCAN_INTERVAL, api, token)
    await coordinator.async_config_entry_first_refresh()

    menuai.data.setdefault(DOMAIN, {})
    menuai.data[DOMAIN][entry.entry_id] = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        menuai.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
