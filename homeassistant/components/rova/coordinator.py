"""Coordinator for Rova."""

from datetime import datetime, timedelta

from rova.rova import Rova

from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers.update_coordinator import DataUpdateCoordinator
from menuai.util.dt import get_time_zone

from .const import DOMAIN, LOGGER

EUROPE_AMSTERDAM_ZONE_INFO = get_time_zone("Europe/Amsterdam")


class RovaCoordinator(DataUpdateCoordinator[dict[str, datetime]]):
    """Class to manage fetching Rova data."""

    config_entry: ConfigEntry

    def __init__(
        self, menuai: menuai, config_entry: ConfigEntry, api: Rova
    ) -> None:
        """Initialize."""
        super().__init__(
            menuai,
            LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=timedelta(hours=12),
        )
        self.api = api

    async def _async_update_data(self) -> dict[str, datetime]:
        """Fetch data from Rova API."""

        items = await self.menuai.async_add_executor_job(self.api.get_calendar_items)

        data = {}

        for item in items:
            date = datetime.strptime(item["Date"], "%Y-%m-%dT%H:%M:%S").replace(
                tzinfo=EUROPE_AMSTERDAM_ZONE_INFO
            )
            code = item["GarbageTypeCode"].lower()
            if code not in data:
                data[code] = date

        return data
