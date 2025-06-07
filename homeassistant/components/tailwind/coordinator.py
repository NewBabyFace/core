"""Data update coordinator for Tailwind."""

from datetime import timedelta

from gotailwind import (
    Tailwind,
    TailwindAuthenticationError,
    TailwindDeviceStatus,
    TailwindError,
)

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_HOST, CONF_TOKEN
from menuai.core import menuai
from menuai.exceptions import ConfigEntryAuthFailed
from menuai.helpers.aiohttp_client import async_get_clientsession
from menuai.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, LOGGER

type TailwindConfigEntry = ConfigEntry[TailwindDataUpdateCoordinator]


class TailwindDataUpdateCoordinator(DataUpdateCoordinator[TailwindDeviceStatus]):
    """Class to manage fetching Tailwind data."""

    def __init__(self, menuai: menuai, entry: TailwindConfigEntry) -> None:
        """Initialize the coordinator."""
        self.tailwind = Tailwind(
            host=entry.data[CONF_HOST],
            token=entry.data[CONF_TOKEN],
            session=async_get_clientsession(menuai),
        )
        super().__init__(
            menuai,
            LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_{entry.data[CONF_HOST]}",
            update_interval=timedelta(seconds=5),
        )

    async def _async_update_data(self) -> TailwindDeviceStatus:
        """Fetch data from the Tailwind device."""
        try:
            return await self.tailwind.status()
        except TailwindAuthenticationError as err:
            raise ConfigEntryAuthFailed from err
        except TailwindError as err:
            raise UpdateFailed(err) from err
