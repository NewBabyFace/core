"""The Nice G.O. integration."""

from __future__ import annotations

import logging

from menuai.const import EVENT_menuai_STOP, Platform
from menuai.core import menuai

from .coordinator import NiceGOConfigEntry, NiceGOUpdateCoordinator

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[Platform] = [
    Platform.COVER,
    Platform.EVENT,
    Platform.LIGHT,
    Platform.SWITCH,
]


async def async_setup_entry(menuai: menuai, entry: NiceGOConfigEntry) -> bool:
    """Set up Nice G.O. from a config entry."""

    coordinator = NiceGOUpdateCoordinator(menuai, entry)
    entry.async_on_unload(
        menuai.bus.async_listen_once(EVENT_menuai_STOP, coordinator.async_ha_stop)
    )

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    entry.async_create_background_task(
        menuai,
        coordinator.client_listen(),
        "nice_go_websocket_task",
    )

    entry.async_on_unload(coordinator.unsubscribe)

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: NiceGOConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.api.close()

    return unload_ok
