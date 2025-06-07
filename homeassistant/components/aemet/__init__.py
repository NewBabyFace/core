"""The AEMET OpenData component."""

import logging
import shutil

from aemet_opendata.exceptions import AemetError, TownNotFound
from aemet_opendata.interface import AEMET, ConnectionOptions, UpdateFeature

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_API_KEY, CONF_LATITUDE, CONF_LONGITUDE, CONF_NAME
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers import aiohttp_client
from menuai.helpers.storage import STORAGE_DIR

from .const import CONF_RADAR_UPDATES, CONF_STATION_UPDATES, DOMAIN, PLATFORMS
from .coordinator import AemetConfigEntry, AemetData, WeatherUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(menuai: menuai, entry: AemetConfigEntry) -> bool:
    """Set up AEMET OpenData as config entry."""
    name = entry.data[CONF_NAME]
    api_key = entry.data[CONF_API_KEY]
    latitude = entry.data[CONF_LATITUDE]
    longitude = entry.data[CONF_LONGITUDE]
    update_features: int = UpdateFeature.FORECAST
    if entry.options.get(CONF_RADAR_UPDATES, False):
        update_features |= UpdateFeature.RADAR
    if entry.options.get(CONF_STATION_UPDATES, True):
        update_features |= UpdateFeature.STATION

    options = ConnectionOptions(api_key, update_features)
    aemet = AEMET(aiohttp_client.async_get_clientsession(menuai), options)
    aemet.set_api_data_dir(menuai.config.path(STORAGE_DIR, f"{DOMAIN}-{entry.unique_id}"))

    try:
        await aemet.select_coordinates(latitude, longitude)
    except TownNotFound as err:
        _LOGGER.error(err)
        return False
    except AemetError as err:
        raise ConfigEntryNotReady(err) from err

    weather_coordinator = WeatherUpdateCoordinator(menuai, entry, aemet)
    await weather_coordinator.async_config_entry_first_refresh()

    entry.runtime_data = AemetData(name=name, coordinator=weather_coordinator)

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def async_update_options(menuai: menuai, entry: ConfigEntry) -> None:
    """Update options."""
    await menuai.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(menuai: menuai, entry: ConfigEntry) -> None:
    """Remove a config entry."""
    await menuai.async_add_executor_job(
        shutil.rmtree,
        menuai.config.path(STORAGE_DIR, f"{DOMAIN}-{entry.unique_id}"),
    )
