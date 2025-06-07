"""The Suez Water integration."""

from __future__ import annotations

import logging

from menuai.const import Platform
from menuai.core import menuai

from .const import CONF_COUNTER_ID
from .coordinator import SuezWaterConfigEntry, SuezWaterCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(menuai: menuai, entry: SuezWaterConfigEntry) -> bool:
    """Set up Suez Water from a config entry."""

    coordinator = SuezWaterCoordinator(menuai, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: SuezWaterConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(
    menuai: menuai, config_entry: SuezWaterConfigEntry
) -> bool:
    """Migrate old suez water config entry."""
    _LOGGER.debug(
        "Migrating configuration from version %s.%s",
        config_entry.version,
        config_entry.minor_version,
    )

    if config_entry.version > 2:
        return False

    if config_entry.version == 1:
        # Migrate to version 2
        counter_id = config_entry.data.get(CONF_COUNTER_ID)
        unique_id = str(counter_id)

        menuai.config_entries.async_update_entry(
            config_entry,
            unique_id=unique_id,
            version=2,
        )

    _LOGGER.debug(
        "Migration to configuration version %s.%s successful",
        config_entry.version,
        config_entry.minor_version,
    )

    return True
