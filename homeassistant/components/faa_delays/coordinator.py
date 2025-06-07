"""DataUpdateCoordinator for faa_delays integration."""

import asyncio
from datetime import timedelta
import logging

from aiohttp import ClientConnectionError
from faadelays import Airport

from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers import aiohttp_client
from menuai.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

type FAAConfigEntry = ConfigEntry[FAADataUpdateCoordinator]


class FAADataUpdateCoordinator(DataUpdateCoordinator[Airport]):
    """Class to manage fetching FAA API data from a single endpoint."""

    def __init__(self, menuai: menuai, entry: FAAConfigEntry, code: str) -> None:
        """Initialize the coordinator."""
        super().__init__(
            menuai,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(minutes=1),
        )
        self.session = aiohttp_client.async_get_clientsession(menuai)
        self.data = Airport(code, self.session)

    async def _async_update_data(self) -> Airport:
        try:
            async with asyncio.timeout(10):
                await self.data.update()
        except ClientConnectionError as err:
            raise UpdateFailed(err) from err
        return self.data
