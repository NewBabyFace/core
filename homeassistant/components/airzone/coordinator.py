"""The Airzone integration."""

from __future__ import annotations

from asyncio import timeout
from datetime import timedelta
import logging
from typing import Any

from aioairzone.exceptions import AirzoneError
from aioairzone.localapi import AirzoneLocalApi

from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import AIOAIRZONE_DEVICE_TIMEOUT_SEC, DOMAIN

SCAN_INTERVAL = timedelta(seconds=60)

_LOGGER = logging.getLogger(__name__)

type AirzoneConfigEntry = ConfigEntry[AirzoneUpdateCoordinator]


class AirzoneUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching data from the Airzone device."""

    config_entry: AirzoneConfigEntry

    def __init__(
        self,
        menuai: menuai,
        config_entry: AirzoneConfigEntry,
        airzone: AirzoneLocalApi,
    ) -> None:
        """Initialize."""
        self.airzone = airzone

        super().__init__(
            menuai,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        async with timeout(AIOAIRZONE_DEVICE_TIMEOUT_SEC):
            try:
                await self.airzone.update()
            except AirzoneError as error:
                raise UpdateFailed(error) from error
            return self.airzone.data()
