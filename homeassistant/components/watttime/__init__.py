"""The WattTime integration."""

from __future__ import annotations

from datetime import timedelta

from aiowatttime import Client
from aiowatttime.emissions import RealTimeEmissionsResponseType
from aiowatttime.errors import InvalidCredentialsError, WattTimeError

from menuai.config_entries import ConfigEntry
from menuai.const import (
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_PASSWORD,
    CONF_USERNAME,
    Platform,
)
from menuai.core import menuai
from menuai.exceptions import ConfigEntryAuthFailed
from menuai.helpers import aiohttp_client
from menuai.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, LOGGER

DEFAULT_UPDATE_INTERVAL = timedelta(minutes=5)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up WattTime from a config entry."""
    session = aiohttp_client.async_get_clientsession(menuai)

    try:
        client = await Client.async_login(
            entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD], session=session
        )
    except InvalidCredentialsError as err:
        raise ConfigEntryAuthFailed("Invalid username/password") from err
    except WattTimeError as err:
        LOGGER.error("Error while authenticating with WattTime: %s", err)
        return False

    async def async_update_data() -> RealTimeEmissionsResponseType:
        """Get the latest realtime emissions data."""
        try:
            return await client.emissions.async_get_realtime_emissions(
                entry.data[CONF_LATITUDE], entry.data[CONF_LONGITUDE]
            )
        except InvalidCredentialsError as err:
            raise ConfigEntryAuthFailed("Invalid username/password") from err
        except WattTimeError as err:
            raise UpdateFailed(
                f"Error while requesting data from WattTime: {err}"
            ) from err

    coordinator = DataUpdateCoordinator(
        menuai,
        LOGGER,
        config_entry=entry,
        name=entry.title,
        update_interval=DEFAULT_UPDATE_INTERVAL,
        update_method=async_update_data,
    )

    await coordinator.async_config_entry_first_refresh()
    menuai.data.setdefault(DOMAIN, {})
    menuai.data[DOMAIN][entry.entry_id] = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        menuai.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_reload_entry(menuai: menuai, config_entry: ConfigEntry) -> None:
    """Handle an options update."""
    await menuai.config_entries.async_reload(config_entry.entry_id)
