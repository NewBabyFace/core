"""The ecoforest coordinator."""

import logging

from pyecoforest.api import EcoforestApi
from pyecoforest.exceptions import EcoforestError
from pyecoforest.models.device import Device

from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import POLLING_INTERVAL

_LOGGER = logging.getLogger(__name__)

type EcoforestConfigEntry = ConfigEntry[EcoforestCoordinator]


class EcoforestCoordinator(DataUpdateCoordinator[Device]):
    """DataUpdateCoordinator to gather data from ecoforest device."""

    def __init__(
        self, menuai: menuai, entry: EcoforestConfigEntry, api: EcoforestApi
    ) -> None:
        """Initialize DataUpdateCoordinator."""

        super().__init__(
            menuai,
            _LOGGER,
            config_entry=entry,
            name="ecoforest",
            update_interval=POLLING_INTERVAL,
        )
        self.api = api

    async def _async_update_data(self) -> Device:
        """Fetch all device and sensor data from api."""
        try:
            data = await self.api.get()
        except EcoforestError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

        _LOGGER.debug("Ecoforest data: %s", data)
        return data
