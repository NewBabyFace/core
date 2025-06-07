"""The coordinator for the Youless integration."""

from datetime import timedelta
import logging

from youless_api import YoulessAPI

from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers.update_coordinator import DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class YouLessCoordinator(DataUpdateCoordinator[None]):
    """Class to manage fetching YouLess data."""

    config_entry: ConfigEntry

    def __init__(
        self, menuai: menuai, config_entry: ConfigEntry, device: YoulessAPI
    ) -> None:
        """Initialize global YouLess data provider."""
        super().__init__(
            menuai,
            _LOGGER,
            config_entry=config_entry,
            name="youless_gateway",
            update_interval=timedelta(seconds=10),
        )
        self.device = device

    async def _async_update_data(self) -> None:
        await self.menuai.async_add_executor_job(self.device.update)
