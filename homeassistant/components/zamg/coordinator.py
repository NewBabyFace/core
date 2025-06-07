"""Data Update coordinator for ZAMG weather data."""

from __future__ import annotations

from zamg import ZamgData as ZamgDevice
from zamg.exceptions import ZamgError, ZamgNoDataError

from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers.aiohttp_client import async_get_clientsession
from menuai.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_STATION_ID, DOMAIN, LOGGER, MIN_TIME_BETWEEN_UPDATES


class ZamgDataUpdateCoordinator(DataUpdateCoordinator[ZamgDevice]):
    """Class to manage fetching ZAMG weather data."""

    config_entry: ConfigEntry
    data: dict = {}
    api_fields: list[str] | None = None

    def __init__(
        self,
        menuai: menuai,
        *,
        entry: ConfigEntry,
    ) -> None:
        """Initialize global ZAMG data updater."""
        self.zamg = ZamgDevice(session=async_get_clientsession(menuai))
        self.zamg.set_default_station(entry.data[CONF_STATION_ID])
        super().__init__(
            menuai,
            LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=MIN_TIME_BETWEEN_UPDATES,
        )

    async def _async_update_data(self) -> ZamgDevice:
        """Fetch data from ZAMG api."""
        try:
            if self.api_fields:
                self.zamg.set_parameters(self.api_fields)
            self.zamg.request_timeout = 60.0
            device = await self.zamg.update()
        except ZamgNoDataError as error:
            raise UpdateFailed("No response from API") from error
        except ZamgError as error:
            raise UpdateFailed(f"Invalid response from API: {error}") from error
        self.data = device
        self.data["last_update"] = self.zamg.last_update
        self.data["Name"] = self.zamg.get_station_name
        return device
