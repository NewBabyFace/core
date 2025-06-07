"""Data Coordinator for Flick Electric."""

import asyncio
from datetime import timedelta
import logging

import aiohttp
from pyflick import FlickAPI, FlickPrice
from pyflick.types import APIException, AuthException

from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.exceptions import ConfigEntryAuthFailed
from menuai.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_SUPPLY_NODE_REF

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=5)

type FlickConfigEntry = ConfigEntry[FlickElectricDataCoordinator]


class FlickElectricDataCoordinator(DataUpdateCoordinator[FlickPrice]):
    """Coordinator for flick power price."""

    config_entry: FlickConfigEntry

    def __init__(
        self,
        menuai: menuai,
        config_entry: FlickConfigEntry,
        api: FlickAPI,
    ) -> None:
        """Initialize FlickElectricDataCoordinator."""
        super().__init__(
            menuai,
            _LOGGER,
            config_entry=config_entry,
            name="Flick Electric",
            update_interval=SCAN_INTERVAL,
        )
        self.supply_node_ref = config_entry.data[CONF_SUPPLY_NODE_REF]
        self._api = api

    async def _async_update_data(self) -> FlickPrice:
        """Fetch pricing data from Flick Electric."""
        try:
            async with asyncio.timeout(60):
                return await self._api.getPricing(self.supply_node_ref)
        except AuthException as err:
            raise ConfigEntryAuthFailed from err
        except (APIException, aiohttp.ClientResponseError) as err:
            raise UpdateFailed from err
