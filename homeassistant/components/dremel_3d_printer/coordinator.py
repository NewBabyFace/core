"""Data update coordinator for the Dremel 3D Printer integration."""

from datetime import timedelta

from dremel3dpy import Dremel3DPrinter

from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, LOGGER

type DremelConfigEntry = ConfigEntry[Dremel3DPrinterDataUpdateCoordinator]


class Dremel3DPrinterDataUpdateCoordinator(DataUpdateCoordinator[None]):
    """Class to manage fetching Dremel 3D Printer data."""

    config_entry: DremelConfigEntry

    def __init__(
        self, menuai: menuai, config_entry: DremelConfigEntry, api: Dremel3DPrinter
    ) -> None:
        """Initialize Dremel 3D Printer data update coordinator."""
        super().__init__(
            menuai=menuai,
            logger=LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=10),
        )
        self.api = api

    async def _async_update_data(self) -> None:
        """Update data via APIs."""
        try:
            await self.menuai.async_add_executor_job(self.api.refresh)
        except RuntimeError as ex:
            raise UpdateFailed(
                f"Unable to refresh printer information: Printer offline: {ex}"
            ) from ex
