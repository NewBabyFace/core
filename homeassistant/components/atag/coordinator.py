"""The ATAG Integration."""

from asyncio import timeout
from datetime import timedelta
import logging

from pyatag import AtagException, AtagOne

from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers.aiohttp_client import async_get_clientsession
from menuai.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)

type AtagConfigEntry = ConfigEntry[AtagDataUpdateCoordinator]


class AtagDataUpdateCoordinator(DataUpdateCoordinator[None]):
    """Atag data update coordinator."""

    config_entry: AtagConfigEntry

    def __init__(self, menuai: menuai, config_entry: AtagConfigEntry) -> None:
        """Initialize Atag coordinator."""
        super().__init__(
            menuai,
            _LOGGER,
            config_entry=config_entry,
            name="Atag",
            update_interval=timedelta(seconds=60),
        )

        self.atag = AtagOne(
            session=async_get_clientsession(menuai),
            **config_entry.data,
            device=config_entry.unique_id,
        )

    async def _async_update_data(self) -> None:
        """Update data via library."""
        async with timeout(20):
            try:
                await self.atag.update()
            except AtagException as err:
                raise UpdateFailed(err) from err
