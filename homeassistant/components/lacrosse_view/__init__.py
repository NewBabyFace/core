"""The LaCrosse View integration."""

from __future__ import annotations

import logging

from lacrosse_view import LaCrosse, LoginError

from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryAuthFailed
from menuai.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN
from .coordinator import LaCrosseUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up LaCrosse View from a config entry."""

    api = LaCrosse(async_get_clientsession(menuai))

    try:
        await api.login(entry.data["username"], entry.data["password"])
        _LOGGER.debug("Log in successful")
    except LoginError as error:
        raise ConfigEntryAuthFailed from error

    coordinator = LaCrosseUpdateCoordinator(menuai, entry, api)

    _LOGGER.debug("First refresh")
    await coordinator.async_config_entry_first_refresh()

    menuai.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
    }

    _LOGGER.debug("Setting up platforms")
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        menuai.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
