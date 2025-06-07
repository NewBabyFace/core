"""The Efergy integration."""

from __future__ import annotations

from pyefergy import Efergy, exceptions

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_API_KEY, Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from menuai.helpers.aiohttp_client import async_get_clientsession

PLATFORMS = [Platform.SENSOR]
type EfergyConfigEntry = ConfigEntry[Efergy]


async def async_setup_entry(menuai: menuai, entry: EfergyConfigEntry) -> bool:
    """Set up Efergy from a config entry."""
    api = Efergy(
        entry.data[CONF_API_KEY],
        session=async_get_clientsession(menuai),
        utc_offset=menuai.config.time_zone,
        currency=menuai.config.currency,
    )

    try:
        await api.async_status(get_sids=True)
    except (exceptions.ConnectError, exceptions.DataError) as ex:
        raise ConfigEntryNotReady(f"Failed to connect to device: {ex}") from ex
    except exceptions.InvalidAuth as ex:
        raise ConfigEntryAuthFailed(
            "API Key is no longer valid. Please reauthenticate"
        ) from ex

    entry.runtime_data = api

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: EfergyConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
