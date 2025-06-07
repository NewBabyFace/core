"""SFR Box coordinator."""

from collections.abc import Callable, Coroutine
from datetime import timedelta
import logging
from typing import Any

from sfrbox_api.bridge import SFRBox
from sfrbox_api.exceptions import SFRBoxError

from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)
_SCAN_INTERVAL = timedelta(minutes=1)


class SFRDataUpdateCoordinator[_DataT](DataUpdateCoordinator[_DataT | None]):
    """Coordinator to manage data updates."""

    config_entry: ConfigEntry

    def __init__(
        self,
        menuai: menuai,
        config_entry: ConfigEntry,
        box: SFRBox,
        name: str,
        method: Callable[[SFRBox], Coroutine[Any, Any, _DataT | None]],
    ) -> None:
        """Initialize coordinator."""
        self.box = box
        self._method = method
        super().__init__(
            menuai,
            _LOGGER,
            config_entry=config_entry,
            name=name,
            update_interval=_SCAN_INTERVAL,
        )

    async def _async_update_data(self) -> _DataT | None:
        """Update data."""
        try:
            return await self._method(self.box)
        except SFRBoxError as err:
            raise UpdateFailed from err
