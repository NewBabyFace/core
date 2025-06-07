"""Support for Neato botvac connected vacuum cleaners."""

from datetime import timedelta
import logging

from pybotvac import Account
from urllib3.response import HTTPResponse

from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.util import Throttle

from .const import NEATO_MAP_DATA, NEATO_PERSISTENT_MAPS, NEATO_ROBOTS

_LOGGER = logging.getLogger(__name__)


class NeatoHub:
    """A My Neato hub wrapper class."""

    def __init__(self, menuai: menuai, neato: Account) -> None:
        """Initialize the Neato hub."""
        self._menuai = menuai
        self.my_neato: Account = neato

    @Throttle(timedelta(minutes=1))
    def update_robots(self) -> None:
        """Update the robot states."""
        _LOGGER.debug("Running HUB.update_robots %s", self._menuai.data.get(NEATO_ROBOTS))
        self._menuai.data[NEATO_ROBOTS] = self.my_neato.robots
        self._menuai.data[NEATO_PERSISTENT_MAPS] = self.my_neato.persistent_maps
        self._menuai.data[NEATO_MAP_DATA] = self.my_neato.maps

    def download_map(self, url: str) -> HTTPResponse:
        """Download a new map image."""
        map_image_data: HTTPResponse = self.my_neato.get_map_image(url)
        return map_image_data

    async def async_update_entry_unique_id(self, entry: ConfigEntry) -> str:
        """Update entry for unique_id."""

        await self._menuai.async_add_executor_job(self.my_neato.refresh_userdata)
        unique_id: str = self.my_neato.unique_id

        if entry.unique_id == unique_id:
            return unique_id

        _LOGGER.debug("Updating user unique_id for previous config entry")
        self._menuai.config_entries.async_update_entry(entry, unique_id=unique_id)
        return unique_id
