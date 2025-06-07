"""Support for Twente Milieu."""

from __future__ import annotations

import voluptuous as vol

from menuai.const import CONF_ID, Platform
from menuai.core import menuai
from menuai.helpers import config_validation as cv

from .coordinator import TwenteMilieuConfigEntry, TwenteMilieuDataUpdateCoordinator

SERVICE_UPDATE = "update"
SERVICE_SCHEMA = vol.Schema({vol.Optional(CONF_ID): cv.string})

PLATFORMS = [Platform.CALENDAR, Platform.SENSOR]


async def async_setup_entry(
    menuai: menuai, entry: TwenteMilieuConfigEntry
) -> bool:
    """Set up Twente Milieu from a config entry."""
    coordinator = TwenteMilieuDataUpdateCoordinator(menuai, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    menuai: menuai, entry: TwenteMilieuConfigEntry
) -> bool:
    """Unload Twente Milieu config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
