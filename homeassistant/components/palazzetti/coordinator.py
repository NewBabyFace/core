"""Helpers to help coordinate updates."""

from pypalazzetti.client import PalazzettiClient
from pypalazzetti.exceptions import CommunicationError, ValidationError

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_HOST
from menuai.core import menuai
from menuai.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, LOGGER, SCAN_INTERVAL

type PalazzettiConfigEntry = ConfigEntry[PalazzettiDataUpdateCoordinator]


class PalazzettiDataUpdateCoordinator(DataUpdateCoordinator[None]):
    """Class to manage fetching Palazzetti data from a Palazzetti hub."""

    config_entry: PalazzettiConfigEntry
    client: PalazzettiClient

    def __init__(
        self,
        menuai: menuai,
        config_entry: PalazzettiConfigEntry,
    ) -> None:
        """Initialize global Palazzetti data updater."""
        super().__init__(
            menuai,
            LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.client = PalazzettiClient(self.config_entry.data[CONF_HOST])

    async def _async_setup(self) -> None:
        try:
            await self.client.connect()
            await self.client.update_state()
        except (CommunicationError, ValidationError) as err:
            raise UpdateFailed(f"Error communicating with the API: {err}") from err

    async def _async_update_data(self) -> None:
        """Fetch data from Palazzetti."""
        try:
            await self.client.update_state()
        except (CommunicationError, ValidationError) as err:
            raise UpdateFailed(f"Error communicating with the API: {err}") from err
