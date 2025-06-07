"""The Huum integration."""

from __future__ import annotations

import logging

from huum.exceptions import Forbidden, NotAuthenticated
from huum.huum import Huum

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_PASSWORD, CONF_USERNAME
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up Huum from a config entry."""
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]

    huum = Huum(username, password, session=async_get_clientsession(menuai))

    try:
        await huum.status()
    except (Forbidden, NotAuthenticated) as err:
        _LOGGER.error("Could not log in to Huum with given credentials")
        raise ConfigEntryNotReady(
            "Could not log in to Huum with given credentials"
        ) from err

    menuai.data.setdefault(DOMAIN, {})[entry.entry_id] = huum

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        menuai.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
