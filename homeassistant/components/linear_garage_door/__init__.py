"""The Linear Garage Door integration."""

from __future__ import annotations

from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import issue_registry as ir

from .const import DOMAIN
from .coordinator import LinearUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.COVER, Platform.LIGHT]


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up Linear Garage Door from a config entry."""

    ir.async_create_issue(
        menuai,
        DOMAIN,
        DOMAIN,
        breaks_in_ha_version="2025.8.0",
        is_fixable=False,
        issue_domain=DOMAIN,
        severity=ir.IssueSeverity.WARNING,
        translation_key="deprecated_integration",
        translation_placeholders={
            "nice_go": "https://www.home-assistant.io/integrations/linear_garage_door",
            "entries": "/config/integrations/integration/linear_garage_door",
        },
    )

    coordinator = LinearUpdateCoordinator(menuai, entry)

    await coordinator.async_config_entry_first_refresh()

    menuai.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        menuai.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_remove_entry(menuai: menuai, entry: ConfigEntry) -> None:
    """Remove a config entry."""
    if not menuai.config_entries.async_loaded_entries(DOMAIN):
        ir.async_delete_issue(menuai, DOMAIN, DOMAIN)
        # Remove any remaining disabled or ignored entries
        for _entry in menuai.config_entries.async_entries(DOMAIN):
            menuai.async_create_task(menuai.config_entries.async_remove(_entry.entry_id))
