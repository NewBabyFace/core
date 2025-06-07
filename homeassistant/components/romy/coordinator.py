"""ROMY coordinator."""

from romy import RomyRobot

from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, LOGGER, UPDATE_INTERVAL


class RomyVacuumCoordinator(DataUpdateCoordinator[None]):
    """ROMY Vacuum Coordinator."""

    config_entry: ConfigEntry

    def __init__(
        self, menuai: menuai, config_entry: ConfigEntry, romy: RomyRobot
    ) -> None:
        """Initialize."""
        super().__init__(
            menuai,
            LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.menuai = menuai
        self.romy = romy

    async def _async_update_data(self) -> None:
        """Update ROMY Vacuum Cleaner data."""
        await self.romy.async_update()
