"""The Bring! integration."""

from __future__ import annotations

import logging

from bring_api import Bring

from menuai.const import CONF_EMAIL, CONF_PASSWORD, Platform
from menuai.core import menuai
from menuai.helpers.aiohttp_client import async_get_clientsession

from .coordinator import (
    BringActivityCoordinator,
    BringConfigEntry,
    BringCoordinators,
    BringDataUpdateCoordinator,
)

PLATFORMS: list[Platform] = [Platform.EVENT, Platform.SENSOR, Platform.TODO]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(menuai: menuai, entry: BringConfigEntry) -> bool:
    """Set up Bring! from a config entry."""

    session = async_get_clientsession(menuai)
    bring = Bring(session, entry.data[CONF_EMAIL], entry.data[CONF_PASSWORD])

    coordinator = BringDataUpdateCoordinator(menuai, entry, bring)
    await coordinator.async_config_entry_first_refresh()

    activity_coordinator = BringActivityCoordinator(menuai, entry, coordinator)
    await activity_coordinator.async_config_entry_first_refresh()

    entry.runtime_data = BringCoordinators(coordinator, activity_coordinator)

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: BringConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
