"""The Nettigo Air Monitor coordinator."""

import logging
from typing import TYPE_CHECKING

from nettigo_air_monitor import (
    ApiError,
    InvalidSensorDataError,
    NAMSensors,
    NettigoAirMonitor,
)
from tenacity import RetryError

from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from menuai.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_UPDATE_INTERVAL, DOMAIN, MANUFACTURER

_LOGGER = logging.getLogger(__name__)

type NAMConfigEntry = ConfigEntry[NAMDataUpdateCoordinator]


class NAMDataUpdateCoordinator(DataUpdateCoordinator[NAMSensors]):
    """Class to manage fetching Nettigo Air Monitor data."""

    config_entry: NAMConfigEntry

    def __init__(
        self,
        menuai: menuai,
        config_entry: NAMConfigEntry,
        nam: NettigoAirMonitor,
    ) -> None:
        """Initialize."""
        if TYPE_CHECKING:
            assert config_entry.unique_id

        self.unique_id = config_entry.unique_id

        self.device_info = DeviceInfo(
            connections={(CONNECTION_NETWORK_MAC, self.unique_id)},
            name="Nettigo Air Monitor",
            sw_version=nam.software_version,
            manufacturer=MANUFACTURER,
            configuration_url=f"http://{nam.host}/",
        )
        self.nam = nam

        super().__init__(
            menuai,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=DEFAULT_UPDATE_INTERVAL,
        )

    async def _async_update_data(self) -> NAMSensors:
        """Update data via library."""
        try:
            data = await self.nam.async_update()
        # We do not need to catch AuthFailed exception here because sensor data is
        # always available without authorization.
        except (ApiError, InvalidSensorDataError, RetryError) as error:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="update_error",
                translation_placeholders={"device": self.config_entry.title},
            ) from error

        return data
