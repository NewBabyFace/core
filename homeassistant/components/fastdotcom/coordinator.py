"""DataUpdateCoordinator for the Fast.com integration."""

from __future__ import annotations

from datetime import timedelta

from fastdotcom import fast_com

from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_INTERVAL, DOMAIN, LOGGER

type FastdotcomConfigEntry = ConfigEntry[FastdotcomDataUpdateCoordinator]


class FastdotcomDataUpdateCoordinator(DataUpdateCoordinator[float]):
    """Class to manage fetching Fast.com data API."""

    def __init__(self, menuai: menuai, entry: FastdotcomConfigEntry) -> None:
        """Initialize the coordinator for Fast.com."""
        super().__init__(
            menuai,
            LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(hours=DEFAULT_INTERVAL),
        )

    async def _async_update_data(self) -> float:
        """Run an executor job to retrieve Fast.com data."""
        try:
            return await self.menuai.async_add_executor_job(fast_com)
        except Exception as exc:
            raise UpdateFailed(f"Error communicating with Fast.com: {exc}") from exc
