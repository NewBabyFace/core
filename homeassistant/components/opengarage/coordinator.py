"""The OpenGarage integration."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

import opengarage

from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers import update_coordinator
from menuai.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class OpenGarageDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching Opengarage data."""

    config_entry: ConfigEntry

    def __init__(
        self,
        menuai: menuai,
        config_entry: ConfigEntry,
        open_garage_connection: opengarage.OpenGarage,
    ) -> None:
        """Initialize global Opengarage data updater."""
        self.open_garage_connection = open_garage_connection

        super().__init__(
            menuai,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=5),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data."""
        data = await self.open_garage_connection.update_state()
        if data is None:
            raise update_coordinator.UpdateFailed(
                "Unable to connect to OpenGarage device"
            )
        return data
