"""DataUpdateCoordinator for the co2signal integration."""

from __future__ import annotations

from datetime import timedelta
import logging

from aioelectricitymaps import (
    CarbonIntensityResponse,
    ElectricityMaps,
    ElectricityMapsError,
    ElectricityMapsInvalidTokenError,
)

from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.exceptions import ConfigEntryAuthFailed
from menuai.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .helpers import fetch_latest_carbon_intensity

_LOGGER = logging.getLogger(__name__)

type CO2SignalConfigEntry = ConfigEntry[CO2SignalCoordinator]


class CO2SignalCoordinator(DataUpdateCoordinator[CarbonIntensityResponse]):
    """Data update coordinator."""

    config_entry: CO2SignalConfigEntry

    def __init__(
        self,
        menuai: menuai,
        config_entry: CO2SignalConfigEntry,
        client: ElectricityMaps,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            menuai,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=timedelta(minutes=15),
        )
        self.client = client

    @property
    def entry_id(self) -> str:
        """Return entry ID."""
        return self.config_entry.entry_id

    async def _async_update_data(self) -> CarbonIntensityResponse:
        """Fetch the latest data from the source."""

        try:
            return await fetch_latest_carbon_intensity(
                self.menuai, self.client, self.config_entry.data
            )
        except ElectricityMapsInvalidTokenError as err:
            raise ConfigEntryAuthFailed from err
        except ElectricityMapsError as err:
            raise UpdateFailed(str(err)) from err
