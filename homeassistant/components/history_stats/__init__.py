"""The history_stats component."""

from __future__ import annotations

from datetime import timedelta

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_ENTITY_ID, CONF_STATE
from menuai.core import menuai
from menuai.helpers.device import (
    async_remove_stale_devices_links_keep_entity_device,
)
from menuai.helpers.template import Template

from .const import CONF_DURATION, CONF_END, CONF_START, PLATFORMS
from .coordinator import HistoryStatsUpdateCoordinator
from .data import HistoryStats

type HistoryStatsConfigEntry = ConfigEntry[HistoryStatsUpdateCoordinator]


async def async_setup_entry(
    menuai: menuai, entry: HistoryStatsConfigEntry
) -> bool:
    """Set up History stats from a config entry."""

    entity_id: str = entry.options[CONF_ENTITY_ID]
    entity_states: list[str] = entry.options[CONF_STATE]
    start: str | None = entry.options.get(CONF_START)
    end: str | None = entry.options.get(CONF_END)

    duration: timedelta | None = None
    if duration_dict := entry.options.get(CONF_DURATION):
        duration = timedelta(**duration_dict)

    history_stats = HistoryStats(
        menuai,
        entity_id,
        entity_states,
        Template(start, menuai) if start else None,
        Template(end, menuai) if end else None,
        duration,
    )
    coordinator = HistoryStatsUpdateCoordinator(menuai, history_stats, entry, entry.title)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    async_remove_stale_devices_links_keep_entity_device(
        menuai,
        entry.entry_id,
        entry.options[CONF_ENTITY_ID],
    )

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True


async def async_unload_entry(
    menuai: menuai, entry: HistoryStatsConfigEntry
) -> bool:
    """Unload History stats config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)


async def update_listener(menuai: menuai, entry: ConfigEntry) -> None:
    """Handle options update."""
    await menuai.config_entries.async_reload(entry.entry_id)
