"""The youless integration."""

import logging
from urllib.error import URLError

from youless_api import YoulessAPI

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_HOST, Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .coordinator import YouLessCoordinator

PLATFORMS = [Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up youless from a config entry."""
    api = YoulessAPI(entry.data[CONF_HOST])

    try:
        await menuai.async_add_executor_job(api.initialize)
    except URLError as exception:
        raise ConfigEntryNotReady from exception

    youless_coordinator = YouLessCoordinator(menuai, entry, api)
    await youless_coordinator.async_config_entry_first_refresh()

    menuai.data.setdefault(DOMAIN, {})
    menuai.data[DOMAIN][entry.entry_id] = youless_coordinator
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        menuai.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
