"""Support for the Swedish weather institute weather service."""

from menuai.const import (
    CONF_LATITUDE,
    CONF_LOCATION,
    CONF_LONGITUDE,
    CONF_NAME,
    Platform,
)
from menuai.core import menuai

from .coordinator import SMHIConfigEntry, SMHIDataUpdateCoordinator

PLATFORMS = [Platform.WEATHER]


async def async_setup_entry(menuai: menuai, entry: SMHIConfigEntry) -> bool:
    """Set up SMHI forecast as config entry."""

    # Setting unique id where missing
    if entry.unique_id is None:
        unique_id = f"{entry.data[CONF_LOCATION][CONF_LATITUDE]}-{entry.data[CONF_LOCATION][CONF_LONGITUDE]}"
        menuai.config_entries.async_update_entry(entry, unique_id=unique_id)

    coordinator = SMHIDataUpdateCoordinator(menuai, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(menuai: menuai, entry: SMHIConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(menuai: menuai, entry: SMHIConfigEntry) -> bool:
    """Migrate old entry."""

    if entry.version > 3:
        # Downgrade from future version
        return False

    if entry.version == 1:
        new_data = {
            CONF_NAME: entry.data[CONF_NAME],
            CONF_LOCATION: {
                CONF_LATITUDE: entry.data[CONF_LATITUDE],
                CONF_LONGITUDE: entry.data[CONF_LONGITUDE],
            },
        }
        menuai.config_entries.async_update_entry(entry, data=new_data, version=2)

    if entry.version == 2:
        new_data = entry.data.copy()
        new_data.pop(CONF_NAME)
        menuai.config_entries.async_update_entry(entry, data=new_data, version=3)

    return True
