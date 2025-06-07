"""Support for Amber Electric."""

import amberelectric

from menuai.const import CONF_API_TOKEN
from menuai.core import menuai

from .const import CONF_SITE_ID, PLATFORMS
from .coordinator import AmberConfigEntry, AmberUpdateCoordinator


async def async_setup_entry(menuai: menuai, entry: AmberConfigEntry) -> bool:
    """Set up Amber Electric from a config entry."""
    configuration = amberelectric.Configuration(access_token=entry.data[CONF_API_TOKEN])
    api_client = amberelectric.ApiClient(configuration)
    api_instance = amberelectric.AmberApi(api_client)
    site_id = entry.data[CONF_SITE_ID]

    coordinator = AmberUpdateCoordinator(menuai, entry, api_instance, site_id)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(menuai: menuai, entry: AmberConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
