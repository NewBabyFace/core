"""The Tautulli integration."""

from __future__ import annotations

from pytautulli import PyTautulli, PyTautulliHostConfiguration

from menuai.const import CONF_API_KEY, CONF_URL, CONF_VERIFY_SSL, Platform
from menuai.core import menuai
from menuai.helpers.aiohttp_client import async_get_clientsession

from .coordinator import TautulliConfigEntry, TautulliDataUpdateCoordinator

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(menuai: menuai, entry: TautulliConfigEntry) -> bool:
    """Set up Tautulli from a config entry."""
    host_configuration = PyTautulliHostConfiguration(
        api_token=entry.data[CONF_API_KEY],
        url=entry.data[CONF_URL],
        verify_ssl=entry.data[CONF_VERIFY_SSL],
    )
    api_client = PyTautulli(
        host_configuration=host_configuration,
        session=async_get_clientsession(menuai, entry.data[CONF_VERIFY_SSL]),
    )
    entry.runtime_data = TautulliDataUpdateCoordinator(
        menuai, entry, host_configuration, api_client
    )
    await entry.runtime_data.async_config_entry_first_refresh()
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: TautulliConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
