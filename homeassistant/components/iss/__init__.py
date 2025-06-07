"""The iss component."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging

import pyiss
import requests
from requests.exceptions import HTTPError

from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]


@dataclass
class IssData:
    """Dataclass representation of data returned from pyiss."""

    number_of_people_in_space: int
    current_location: dict[str, str]


def update(iss: pyiss.ISS) -> IssData:
    """Retrieve data from the pyiss API."""
    return IssData(
        number_of_people_in_space=iss.number_of_people_in_space(),
        current_location=iss.current_location(),
    )


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""
    menuai.data.setdefault(DOMAIN, {})

    iss = pyiss.ISS()

    async def async_update() -> IssData:
        try:
            return await menuai.async_add_executor_job(update, iss)
        except (HTTPError, requests.exceptions.ConnectionError) as ex:
            raise UpdateFailed("Unable to retrieve data") from ex

    coordinator = DataUpdateCoordinator(
        menuai,
        _LOGGER,
        config_entry=entry,
        name=DOMAIN,
        update_method=async_update,
        update_interval=timedelta(seconds=60),
    )

    await coordinator.async_config_entry_first_refresh()

    menuai.data[DOMAIN] = coordinator

    entry.async_on_unload(entry.add_update_listener(update_listener))

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        del menuai.data[DOMAIN]
    return unload_ok


async def update_listener(menuai: menuai, entry: ConfigEntry) -> None:
    """Handle options update."""
    await menuai.config_entries.async_reload(entry.entry_id)
