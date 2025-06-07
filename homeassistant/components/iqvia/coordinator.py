"""Support for IQVIA."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from datetime import timedelta
from typing import Any

from pyiqvia.errors import IQVIAError

from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import LOGGER

DEFAULT_SCAN_INTERVAL = timedelta(minutes=30)

type IqviaConfigEntry = ConfigEntry[dict[str, IqviaUpdateCoordinator]]


class IqviaUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Custom DataUpdateCoordinator for IQVIA."""

    config_entry: IqviaConfigEntry

    def __init__(
        self,
        menuai: menuai,
        config_entry: IqviaConfigEntry,
        name: str,
        update_method: Callable[[], Coroutine[Any, Any, dict[str, Any]]],
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            menuai,
            LOGGER,
            name=name,
            config_entry=config_entry,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self._update_method = update_method

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the API."""
        try:
            return await self._update_method()
        except IQVIAError as err:
            raise UpdateFailed from err
