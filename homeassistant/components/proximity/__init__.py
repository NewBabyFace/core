"""Support for tracking the proximity of a device."""

from __future__ import annotations

import logging

from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers.event import (
    async_track_entity_registry_updated_event,
    async_track_state_change_event,
)

from .const import CONF_TRACKED_ENTITIES
from .coordinator import ProximityConfigEntry, ProximityDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(menuai: menuai, entry: ProximityConfigEntry) -> bool:
    """Set up Proximity from a config entry."""
    _LOGGER.debug("setup %s with config:%s", entry.title, entry.data)

    coordinator = ProximityDataUpdateCoordinator(menuai, entry)

    entry.async_on_unload(
        async_track_state_change_event(
            menuai,
            entry.data[CONF_TRACKED_ENTITIES],
            coordinator.async_check_proximity_state_change,
        )
    )

    entry.async_on_unload(
        async_track_entity_registry_updated_event(
            menuai,
            entry.data[CONF_TRACKED_ENTITIES],
            coordinator.async_check_tracked_entity_change,
        )
    )

    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, [Platform.SENSOR])
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(menuai: menuai, entry: ProximityConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, [Platform.SENSOR])


async def _async_update_listener(
    menuai: menuai, entry: ProximityConfigEntry
) -> None:
    """Handle options update."""
    await menuai.config_entries.async_reload(entry.entry_id)
