"""The qnap component."""

from __future__ import annotations

from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai

from .const import DOMAIN
from .coordinator import QnapCoordinator

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
]


async def async_setup_entry(menuai: menuai, config_entry: ConfigEntry) -> bool:
    """Set the config entry up."""
    menuai.data.setdefault(DOMAIN, {})
    coordinator = QnapCoordinator(menuai, config_entry)
    # Fetch initial data so we have data when entities subscribe
    await coordinator.async_config_entry_first_refresh()
    menuai.data[DOMAIN][config_entry.entry_id] = coordinator
    await menuai.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    return True


async def async_unload_entry(menuai: menuai, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await menuai.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    ):
        menuai.data[DOMAIN].pop(config_entry.entry_id)
    return unload_ok
