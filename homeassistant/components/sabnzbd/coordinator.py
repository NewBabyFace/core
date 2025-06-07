"""DataUpdateCoordinator for the SABnzbd integration."""

from datetime import timedelta
import logging
from typing import Any

from pysabnzbd import SabnzbdApi, SabnzbdApiException

from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)

type SabnzbdConfigEntry = ConfigEntry[SabnzbdUpdateCoordinator]


class SabnzbdUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """The SABnzbd update coordinator."""

    config_entry: SabnzbdConfigEntry

    def __init__(
        self,
        menuai: menuai,
        config_entry: SabnzbdConfigEntry,
        sab_api: SabnzbdApi,
    ) -> None:
        """Initialize the SABnzbd update coordinator."""
        self.sab_api = sab_api

        super().__init__(
            menuai,
            _LOGGER,
            config_entry=config_entry,
            name="SABnzbd",
            update_interval=timedelta(seconds=30),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Get the latest data from the SABnzbd API."""
        try:
            await self.sab_api.refresh_data()
        except SabnzbdApiException as err:
            raise UpdateFailed("Error while fetching data") from err

        return self.sab_api.queue
