"""Smarty Coordinator."""

from datetime import timedelta
import logging

from pysmarty2 import Smarty

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_HOST
from menuai.core import menuai
from menuai.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)

type SmartyConfigEntry = ConfigEntry[SmartyCoordinator]


class SmartyCoordinator(DataUpdateCoordinator[None]):
    """Smarty Coordinator."""

    config_entry: SmartyConfigEntry
    software_version: str
    configuration_version: str

    def __init__(self, menuai: menuai, config_entry: SmartyConfigEntry) -> None:
        """Initialize."""
        super().__init__(
            menuai,
            logger=_LOGGER,
            config_entry=config_entry,
            name="Smarty",
            update_interval=timedelta(seconds=30),
        )
        self.client = Smarty(host=config_entry.data[CONF_HOST])

    async def _async_setup(self) -> None:
        if not await self.menuai.async_add_executor_job(self.client.update):
            raise UpdateFailed("Failed to update Smarty data")
        self.software_version = self.client.get_software_version()
        self.configuration_version = self.client.get_configuration_version()

    async def _async_update_data(self) -> None:
        """Fetch data from Smarty."""
        if not await self.menuai.async_add_executor_job(self.client.update):
            raise UpdateFailed("Failed to update Smarty data")
