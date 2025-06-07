"""JustNimbus coordinator."""

from __future__ import annotations

from datetime import timedelta
import logging

import justnimbus

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_CLIENT_ID
from menuai.core import menuai
from menuai.helpers.update_coordinator import DataUpdateCoordinator

from .const import CONF_ZIP_CODE, DOMAIN

_LOGGER = logging.getLogger(__name__)


class JustNimbusCoordinator(DataUpdateCoordinator[justnimbus.JustNimbusModel]):
    """Data update coordinator."""

    config_entry: ConfigEntry

    def __init__(self, menuai: menuai, config_entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            menuai,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=timedelta(minutes=1),
        )
        self._client = justnimbus.JustNimbusClient(
            client_id=config_entry.data[CONF_CLIENT_ID],
            zip_code=config_entry.data[CONF_ZIP_CODE],
        )

    async def _async_update_data(self) -> justnimbus.JustNimbusModel:
        """Fetch the latest data from the source."""
        return await self.menuai.async_add_executor_job(self._client.get_data)
