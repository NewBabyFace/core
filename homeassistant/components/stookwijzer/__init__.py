"""The Stookwijzer integration."""

from __future__ import annotations

from typing import Any

from stookwijzer import Stookwijzer

from menuai.const import CONF_LATITUDE, CONF_LOCATION, CONF_LONGITUDE, Platform
from menuai.core import menuai, callback
from menuai.helpers import entity_registry as er, issue_registry as ir

from .const import DOMAIN, LOGGER
from .coordinator import StookwijzerConfigEntry, StookwijzerCoordinator

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(menuai: menuai, entry: StookwijzerConfigEntry) -> bool:
    """Set up Stookwijzer from a config entry."""
    await er.async_migrate_entries(menuai, entry.entry_id, async_migrate_entity_entry)

    coordinator = StookwijzerCoordinator(menuai, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    menuai: menuai, entry: StookwijzerConfigEntry
) -> bool:
    """Unload Stookwijzer config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(
    menuai: menuai, entry: StookwijzerConfigEntry
) -> bool:
    """Migrate old entry."""
    LOGGER.debug("Migrating from version %s", entry.version)

    if entry.version == 1:
        xy = await Stookwijzer.async_transform_coordinates(
            entry.data[CONF_LOCATION][CONF_LATITUDE],
            entry.data[CONF_LOCATION][CONF_LONGITUDE],
        )

        if not xy:
            ir.async_create_issue(
                menuai,
                DOMAIN,
                "location_migration_failed",
                is_fixable=False,
                severity=ir.IssueSeverity.ERROR,
                translation_key="location_migration_failed",
                translation_placeholders={
                    "entry_title": entry.title,
                },
            )
            return False

        menuai.config_entries.async_update_entry(
            entry,
            version=2,
            data={
                CONF_LATITUDE: xy["x"],
                CONF_LONGITUDE: xy["y"],
            },
        )

        LOGGER.debug("Migration to version %s successful", entry.version)

    return True


@callback
def async_migrate_entity_entry(entity_entry: er.RegistryEntry) -> dict[str, Any] | None:
    """Migrate Stookwijzer entity entries.

    - Migrates unique ID for the old Stookwijzer sensors to the new unique ID.
    """
    if entity_entry.unique_id == entity_entry.config_entry_id:
        return {"new_unique_id": f"{entity_entry.config_entry_id}_advice"}

    # No migration needed
    return None
