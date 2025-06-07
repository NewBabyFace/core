"""The Electra Air Conditioner integration."""

from __future__ import annotations

from electrasmart.api import ElectraAPI, ElectraApiError

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_TOKEN, Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_IMEI

PLATFORMS: list[Platform] = [Platform.CLIMATE]

type ElectraSmartConfigEntry = ConfigEntry[ElectraAPI]


async def async_setup_entry(
    menuai: menuai, entry: ElectraSmartConfigEntry
) -> bool:
    """Set up Electra Smart Air Conditioner from a config entry."""
    api = ElectraAPI(
        async_get_clientsession(menuai), entry.data[CONF_IMEI], entry.data[CONF_TOKEN]
    )
    try:
        await api.fetch_devices()
    except ElectraApiError as exp:
        raise ConfigEntryNotReady(f"Error communicating with API: {exp}") from exp

    entry.async_on_unload(entry.add_update_listener(update_listener))
    entry.runtime_data = api
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    menuai: menuai, entry: ElectraSmartConfigEntry
) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)


async def update_listener(
    menuai: menuai, config_entry: ElectraSmartConfigEntry
) -> None:
    """Update listener."""
    await menuai.config_entries.async_reload(config_entry.entry_id)
