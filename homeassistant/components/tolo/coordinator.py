"""Component to control TOLO Sauna/Steam Bath."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import NamedTuple

from tololib import ToloClient, ToloSettings, ToloStatus

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_HOST
from menuai.core import menuai
from menuai.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_RETRY_COUNT, DEFAULT_RETRY_TIMEOUT

_LOGGER = logging.getLogger(__name__)


class ToloSaunaData(NamedTuple):
    """Compound class for reflecting full state (status and info) of a TOLO Sauna."""

    status: ToloStatus
    settings: ToloSettings


class ToloSaunaUpdateCoordinator(DataUpdateCoordinator[ToloSaunaData]):
    """DataUpdateCoordinator for TOLO Sauna."""

    config_entry: ConfigEntry

    def __init__(self, menuai: menuai, entry: ConfigEntry) -> None:
        """Initialize ToloSaunaUpdateCoordinator."""
        self.client = ToloClient(
            address=entry.data[CONF_HOST],
            retry_timeout=DEFAULT_RETRY_TIMEOUT,
            retry_count=DEFAULT_RETRY_COUNT,
        )
        super().__init__(
            menuai=menuai,
            logger=_LOGGER,
            config_entry=entry,
            name=f"{entry.title} ({entry.data[CONF_HOST]}) Data Update Coordinator",
            update_interval=timedelta(seconds=5),
        )

    async def _async_update_data(self) -> ToloSaunaData:
        return await self.menuai.async_add_executor_job(self._get_tolo_sauna_data)

    def _get_tolo_sauna_data(self) -> ToloSaunaData:
        try:
            status = self.client.get_status()
            settings = self.client.get_settings()
        except TimeoutError as error:
            raise UpdateFailed("communication timeout") from error
        return ToloSaunaData(status, settings)
