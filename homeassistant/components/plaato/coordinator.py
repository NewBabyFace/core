"""Coordinator for Plaato devices."""

from datetime import timedelta
import logging

from pyplaato.plaato import Plaato, PlaatoDeviceType

from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import aiohttp_client
from menuai.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class PlaatoCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    config_entry: ConfigEntry

    def __init__(
        self,
        menuai: menuai,
        config_entry: ConfigEntry,
        auth_token: str,
        device_type: PlaatoDeviceType,
        update_interval: timedelta,
    ) -> None:
        """Initialize."""
        self.api = Plaato(auth_token=auth_token)
        self.menuai = menuai
        self.device_type = device_type
        self.platforms: list[Platform] = []

        super().__init__(
            menuai,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=update_interval,
        )

    async def _async_update_data(self):
        """Update data via library."""
        return await self.api.get_data(
            session=aiohttp_client.async_get_clientsession(self.menuai),
            device_type=self.device_type,
        )
