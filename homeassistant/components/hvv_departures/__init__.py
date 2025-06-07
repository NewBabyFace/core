"""The HVV integration."""

from menuai.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, Platform
from menuai.core import menuai
from menuai.helpers import aiohttp_client

from .hub import GTIHub, HVVConfigEntry

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR]


async def async_setup_entry(menuai: menuai, entry: HVVConfigEntry) -> bool:
    """Set up HVV from a config entry."""

    hub = GTIHub(
        entry.data[CONF_HOST],
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        aiohttp_client.async_get_clientsession(menuai),
    )

    entry.runtime_data = hub

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: HVVConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
