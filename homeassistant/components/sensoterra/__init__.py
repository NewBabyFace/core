"""The Sensoterra integration."""

from __future__ import annotations

from sensoterra.customerapi import CustomerApi

from menuai.const import CONF_TOKEN, Platform
from menuai.core import menuai

from .coordinator import SensoterraConfigEntry, SensoterraCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(menuai: menuai, entry: SensoterraConfigEntry) -> bool:
    """Set up Sensoterra platform based on a configuration entry."""

    # Create a coordinator and add an API instance to it. Store the coordinator
    # in the configuration entry.
    api = CustomerApi()
    api.set_language(menuai.config.language)
    api.set_token(entry.data[CONF_TOKEN])

    coordinator = SensoterraCoordinator(menuai, entry, api)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: SensoterraConfigEntry) -> bool:
    """Unload the configuration entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
