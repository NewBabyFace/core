"""The trafikverket_train component."""

from __future__ import annotations

import logging

from pytrafikverket import (
    InvalidAuthentication,
    NoTrainStationFound,
    TrafikverketTrain,
    UnknownError,
)

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_API_KEY
from menuai.core import menuai
from menuai.exceptions import ConfigEntryAuthFailed
from menuai.helpers import entity_registry as er
from menuai.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_FROM, CONF_TO, PLATFORMS
from .coordinator import TVDataUpdateCoordinator

TVTrainConfigEntry = ConfigEntry[TVDataUpdateCoordinator]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(menuai: menuai, entry: TVTrainConfigEntry) -> bool:
    """Set up Trafikverket Train from a config entry."""

    coordinator = TVDataUpdateCoordinator(menuai, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    entity_reg = er.async_get(menuai)
    entries = er.async_entries_for_config_entry(entity_reg, entry.entry_id)
    for entity in entries:
        if not entity.unique_id.startswith(entry.entry_id):
            entity_reg.async_update_entity(
                entity.entity_id, new_unique_id=f"{entry.entry_id}-departure_time"
            )

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True


async def async_unload_entry(menuai: menuai, entry: TVTrainConfigEntry) -> bool:
    """Unload Trafikverket Weatherstation config entry."""

    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)


async def update_listener(menuai: menuai, entry: TVTrainConfigEntry) -> None:
    """Handle options update."""
    await menuai.config_entries.async_reload(entry.entry_id)


async def async_migrate_entry(menuai: menuai, entry: TVTrainConfigEntry) -> bool:
    """Migrate config entry."""
    _LOGGER.debug("Migrating from version %s", entry.version)

    if entry.version > 2:
        # This means the user has downgraded from a future version
        return False

    if entry.version == 1:
        if entry.minor_version == 1:
            # Remove unique id
            menuai.config_entries.async_update_entry(
                entry, unique_id=None, minor_version=2
            )

        # Change from station names to station signatures
        try:
            web_session = async_get_clientsession(menuai)
            train_api = TrafikverketTrain(web_session, entry.data[CONF_API_KEY])
            from_stations = await train_api.async_search_train_stations(
                entry.data[CONF_FROM]
            )
            to_stations = await train_api.async_search_train_stations(
                entry.data[CONF_TO]
            )
        except InvalidAuthentication as error:
            raise ConfigEntryAuthFailed from error
        except NoTrainStationFound as error:
            _LOGGER.error(
                "Migration failed as no train station found with provided name %s",
                str(error),
            )
            return False
        except UnknownError as error:
            _LOGGER.error("Unknown error occurred during validation %s", str(error))
            return False
        except Exception as error:  # noqa: BLE001
            _LOGGER.error("Unknown exception occurred during validation %s", str(error))
            return False

        if len(from_stations) > 1 or len(to_stations) > 1:
            _LOGGER.error(
                "Migration failed as more than one station found with provided name"
            )
            return False

        new_data = entry.data.copy()
        new_data[CONF_FROM] = from_stations[0].signature
        new_data[CONF_TO] = to_stations[0].signature

        menuai.config_entries.async_update_entry(
            entry, data=new_data, version=2, minor_version=1
        )

    _LOGGER.debug(
        "Migration to version %s.%s successful",
        entry.version,
        entry.minor_version,
    )

    return True
