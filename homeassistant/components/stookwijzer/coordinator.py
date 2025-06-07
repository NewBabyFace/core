"""Class representing a Stookwijzer update coordinator."""

from datetime import timedelta

from stookwijzer import Stookwijzer

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_LATITUDE, CONF_LONGITUDE
from menuai.core import menuai
from menuai.helpers.aiohttp_client import async_get_clientsession
from menuai.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, LOGGER

SCAN_INTERVAL = timedelta(minutes=60)

type StookwijzerConfigEntry = ConfigEntry[StookwijzerCoordinator]


class StookwijzerCoordinator(DataUpdateCoordinator[None]):
    """Stookwijzer update coordinator."""

    config_entry: StookwijzerConfigEntry

    def __init__(
        self, menuai: menuai, config_entry: StookwijzerConfigEntry
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            menuai,
            LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.client = Stookwijzer(
            async_get_clientsession(menuai),
            config_entry.data[CONF_LATITUDE],
            config_entry.data[CONF_LONGITUDE],
        )

    async def _async_update_data(self) -> None:
        """Fetch data from API endpoint."""
        await self.client.async_update()
        if self.client.advice is None:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="no_data_received",
            )
