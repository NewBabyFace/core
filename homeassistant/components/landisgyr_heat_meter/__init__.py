"""The Landis+Gyr Heat Meter integration."""

from __future__ import annotations

import logging
from typing import Any

import ultraheat_api

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_DEVICE, Platform
from menuai.core import menuai, callback
from menuai.helpers.entity_registry import RegistryEntry, async_migrate_entries

from .const import DOMAIN
from .coordinator import UltraheatCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up heat meter from a config entry."""

    _LOGGER.debug("Initializing %s integration on %s", DOMAIN, entry.data[CONF_DEVICE])
    reader = ultraheat_api.UltraheatReader(entry.data[CONF_DEVICE])
    api = ultraheat_api.HeatMeterService(reader)

    coordinator = UltraheatCoordinator(menuai, entry, api)
    await coordinator.async_config_entry_first_refresh()

    menuai.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        menuai.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_migrate_entry(menuai: menuai, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %s", config_entry.version)

    # Removing domain name and config entry id from entity unique id's, replacing it with device number
    if config_entry.version == 1:
        menuai.config_entries.async_update_entry(config_entry, version=2)

        device_number = config_entry.data["device_number"]

        @callback
        def update_entity_unique_id(
            entity_entry: RegistryEntry,
        ) -> dict[str, Any] | None:
            """Update unique ID of entity entry."""
            if entity_entry.platform in entity_entry.unique_id:
                return {
                    "new_unique_id": entity_entry.unique_id.replace(
                        f"{entity_entry.platform}_{entity_entry.config_entry_id}",
                        f"{device_number}",
                    )
                }
            return None

        await async_migrate_entries(
            menuai, config_entry.entry_id, update_entity_unique_id
        )

    _LOGGER.debug("Migration to version %s successful", config_entry.version)

    return True
