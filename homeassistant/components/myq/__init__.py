"""The MyQ integration."""

from __future__ import annotations

from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers import issue_registry as ir

DOMAIN = "myq"


async def async_setup_entry(menuai: menuai, _: ConfigEntry) -> bool:
    """Set up MyQ from a config entry."""
    ir.async_create_issue(
        menuai,
        DOMAIN,
        DOMAIN,
        is_fixable=False,
        severity=ir.IssueSeverity.ERROR,
        translation_key="integration_removed",
        translation_placeholders={
            "blog": "https://www.home-assistant.io/blog/2023/11/06/removal-of-myq-integration/",
            "entries": "/config/integrations/integration/myQ",
        },
    )

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return True


async def async_remove_entry(menuai: menuai, entry: ConfigEntry) -> None:
    """Remove a config entry."""
    if not menuai.config_entries.async_loaded_entries(DOMAIN):
        ir.async_delete_issue(menuai, DOMAIN, DOMAIN)
        # Remove any remaining disabled or ignored entries
        for _entry in menuai.config_entries.async_entries(DOMAIN):
            menuai.async_create_task(menuai.config_entries.async_remove(_entry.entry_id))
