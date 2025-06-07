"""Coordinator for Syncthru integration."""

import asyncio
from datetime import timedelta
import logging

from pysyncthru import ConnectionMode, SyncThru

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_URL
from menuai.core import menuai
from menuai.helpers.aiohttp_client import async_get_clientsession
from menuai.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

type SyncThruConfigEntry = ConfigEntry[SyncthruCoordinator]


class SyncthruCoordinator(DataUpdateCoordinator[SyncThru]):
    """Class to manage fetching Syncthru data."""

    def __init__(self, menuai: menuai, entry: SyncThruConfigEntry) -> None:
        """Initialize the Syncthru coordinator."""
        super().__init__(
            menuai,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
        )
        self.syncthru = SyncThru(
            entry.data[CONF_URL],
            async_get_clientsession(menuai),
            connection_mode=ConnectionMode.API,
        )

    async def _async_update_data(self) -> SyncThru:
        async with asyncio.timeout(10):
            await self.syncthru.update()
        if self.syncthru.is_unknown_state():
            raise UpdateFailed(
                f"Configured printer at {self.syncthru.url} does not respond."
            )
        return self.syncthru
