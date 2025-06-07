"""The Monarch Money integration."""

from __future__ import annotations

from typedmonarchmoney import TypedMonarchMoney

from menuai.const import CONF_TOKEN, Platform
from menuai.core import menuai

from .coordinator import MonarchMoneyConfigEntry, MonarchMoneyDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(
    menuai: menuai, entry: MonarchMoneyConfigEntry
) -> bool:
    """Set up Monarch Money from a config entry."""
    monarch_client = TypedMonarchMoney(token=entry.data.get(CONF_TOKEN))

    mm_coordinator = MonarchMoneyDataUpdateCoordinator(menuai, entry, monarch_client)
    await mm_coordinator.async_config_entry_first_refresh()
    entry.runtime_data = mm_coordinator
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    menuai: menuai, entry: MonarchMoneyConfigEntry
) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
