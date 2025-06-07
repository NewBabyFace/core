"""Update coordinator for Tile."""

from datetime import timedelta

from pytile.api import API
from pytile.errors import InvalidAuthError, SessionExpiredError, TileError
from pytile.tile import Tile

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_USERNAME
from menuai.core import menuai
from menuai.exceptions import ConfigEntryAuthFailed
from menuai.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import LOGGER

type TileConfigEntry = ConfigEntry[dict[str, TileCoordinator]]


class TileCoordinator(DataUpdateCoordinator[None]):
    """Define an object to coordinate Tile data retrieval."""

    config_entry: TileConfigEntry

    def __init__(
        self, menuai: menuai, entry: TileConfigEntry, client: API, tile: Tile
    ) -> None:
        """Initialize."""
        super().__init__(
            menuai,
            LOGGER,
            name=tile.name,
            config_entry=entry,
            update_interval=timedelta(minutes=2),
        )
        self.tile = tile
        self.client = client
        self.username = entry.data[CONF_USERNAME]

    async def _async_update_data(self) -> None:
        """Update data via library."""
        try:
            await self.tile.async_update()
        except InvalidAuthError as err:
            raise ConfigEntryAuthFailed("Invalid credentials") from err
        except SessionExpiredError:
            LOGGER.debug("Tile session expired; creating a new one")
            await self.client.async_init()
        except TileError as err:
            raise UpdateFailed(f"Error while retrieving data: {err}") from err
