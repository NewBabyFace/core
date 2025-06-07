"""Coordinator for the SensorPush Cloud integration."""

from __future__ import annotations

from sensorpush_ha import (
    SensorPushCloudApi,
    SensorPushCloudData,
    SensorPushCloudError,
    SensorPushCloudHelper,
)

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_EMAIL, CONF_PASSWORD
from menuai.core import menuai
from menuai.helpers.aiohttp_client import async_get_clientsession
from menuai.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import LOGGER, UPDATE_INTERVAL

type SensorPushCloudConfigEntry = ConfigEntry[SensorPushCloudCoordinator]


class SensorPushCloudCoordinator(DataUpdateCoordinator[dict[str, SensorPushCloudData]]):
    """SensorPush Cloud coordinator."""

    def __init__(self, menuai: menuai, entry: SensorPushCloudConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            menuai,
            LOGGER,
            name=entry.title,
            update_interval=UPDATE_INTERVAL,
            config_entry=entry,
        )
        email, password = entry.data[CONF_EMAIL], entry.data[CONF_PASSWORD]
        clientsession = async_get_clientsession(menuai)
        api = SensorPushCloudApi(email, password, clientsession)
        self.helper = SensorPushCloudHelper(api)

    async def _async_update_data(self) -> dict[str, SensorPushCloudData]:
        """Fetch data from API endpoints."""
        try:
            return await self.helper.async_get_data()
        except SensorPushCloudError as e:
            raise UpdateFailed(e) from e
