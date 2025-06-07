"""Coordinator for radiotherm."""

from __future__ import annotations

from datetime import timedelta
import logging
from urllib.error import URLError

from radiotherm.validate import RadiothermTstatError

from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .data import RadioThermInitData, RadioThermUpdate, async_get_data

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(seconds=15)


class RadioThermUpdateCoordinator(DataUpdateCoordinator[RadioThermUpdate]):
    """DataUpdateCoordinator to gather data for radio thermostats."""

    config_entry: ConfigEntry

    def __init__(
        self,
        menuai: menuai,
        config_entry: ConfigEntry,
        init_data: RadioThermInitData,
    ) -> None:
        """Initialize DataUpdateCoordinator."""
        self.init_data = init_data
        self._description = f"{init_data.name} ({init_data.host})"
        super().__init__(
            menuai,
            _LOGGER,
            config_entry=config_entry,
            name=f"radiotherm {self.init_data.name}",
            update_interval=UPDATE_INTERVAL,
        )

    async def _async_update_data(self) -> RadioThermUpdate:
        """Update data from the thermostat."""
        try:
            return await async_get_data(self.menuai, self.init_data.tstat)
        except RadiothermTstatError as ex:
            msg = f"{self._description} was busy (invalid value returned): {ex}"
            raise UpdateFailed(msg) from ex
        except TimeoutError as ex:
            msg = f"{self._description}) timed out waiting for a response: {ex}"
            raise UpdateFailed(msg) from ex
        except (OSError, URLError) as ex:
            msg = f"{self._description} connection error: {ex}"
            raise UpdateFailed(msg) from ex
