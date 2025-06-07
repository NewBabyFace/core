"""The Remote Calendar integration."""

import logging

from menuai.const import Platform
from menuai.core import menuai

from .const import DOMAIN
from .coordinator import RemoteCalendarConfigEntry, RemoteCalendarDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


PLATFORMS: list[Platform] = [Platform.CALENDAR]


async def async_setup_entry(
    menuai: menuai, entry: RemoteCalendarConfigEntry
) -> bool:
    """Set up Remote Calendar from a config entry."""
    menuai.data.setdefault(DOMAIN, {})
    coordinator = RemoteCalendarDataUpdateCoordinator(menuai, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    menuai: menuai, entry: RemoteCalendarConfigEntry
) -> bool:
    """Handle unload of an entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
