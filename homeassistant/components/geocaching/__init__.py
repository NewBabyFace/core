"""The Geocaching integration."""

from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers.config_entry_oauth2_flow import (
    OAuth2Session,
    async_get_config_entry_implementation,
)

from .coordinator import GeocachingConfigEntry, GeocachingDataUpdateCoordinator

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(menuai: menuai, entry: GeocachingConfigEntry) -> bool:
    """Set up Geocaching from a config entry."""
    implementation = await async_get_config_entry_implementation(menuai, entry)

    oauth_session = OAuth2Session(menuai, entry, implementation)
    coordinator = GeocachingDataUpdateCoordinator(
        menuai, entry=entry, session=oauth_session
    )

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: GeocachingConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
