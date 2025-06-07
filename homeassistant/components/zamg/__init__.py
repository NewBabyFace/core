"""The zamg component."""

from __future__ import annotations

from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai, callback
from menuai.helpers import entity_registry as er

from .const import CONF_STATION_ID, DOMAIN, LOGGER
from .coordinator import ZamgDataUpdateCoordinator

PLATFORMS = (Platform.SENSOR, Platform.WEATHER)


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up Zamg from config entry."""
    await _async_migrate_entries(menuai, entry)

    coordinator = ZamgDataUpdateCoordinator(menuai, entry=entry)
    station_id = entry.data[CONF_STATION_ID]
    coordinator.zamg.set_default_station(station_id)
    await coordinator.async_config_entry_first_refresh()

    menuai.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Set up all platforms for this device/entry.
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload ZAMG config entry."""
    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        menuai.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def _async_migrate_entries(
    menuai: menuai, config_entry: ConfigEntry
) -> bool:
    """Migrate old entry."""
    entity_registry = er.async_get(menuai)

    @callback
    def update_unique_id(entry: er.RegistryEntry) -> dict[str, str] | None:
        """Convert the unique_id from 'name_stationid' to 'station_id'.

        Example: 'WIEN/HOHE WARTE_11035' --> '11035'.
        """
        if (
            entry.domain == Platform.WEATHER
            and entry.unique_id != config_entry.data[CONF_STATION_ID]
        ):
            new_unique_id = config_entry.data[CONF_STATION_ID]
            LOGGER.debug(
                "Migrating entity '%s' unique_id from '%s' to '%s'",
                entry.entity_id,
                entry.unique_id,
                new_unique_id,
            )
            if existing_entity_id := entity_registry.async_get_entity_id(
                entry.domain, entry.platform, new_unique_id
            ):
                LOGGER.debug(
                    "Cannot migrate to unique_id '%s', already exists for '%s'",
                    new_unique_id,
                    existing_entity_id,
                )
                return None
            return {
                "new_unique_id": new_unique_id,
            }
        return None

    await er.async_migrate_entries(menuai, config_entry.entry_id, update_unique_id)

    return True
