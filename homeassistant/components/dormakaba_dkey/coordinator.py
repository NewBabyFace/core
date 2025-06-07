"""Coordinator for the Dormakaba dKey integration."""

from __future__ import annotations

from datetime import timedelta
import logging

from py_dormakaba_dkey import DKEYLock
from py_dormakaba_dkey.errors import DKEY_EXCEPTIONS, NotAssociated

from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.exceptions import ConfigEntryAuthFailed
from menuai.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import UPDATE_SECONDS

_LOGGER = logging.getLogger(__name__)

type DormakabaDkeyConfigEntry = ConfigEntry[DormakabaDkeyCoordinator]


class DormakabaDkeyCoordinator(DataUpdateCoordinator[None]):
    """DormakabaDkey coordinator."""

    def __init__(
        self,
        menuai: menuai,
        entry: DormakabaDkeyConfigEntry,
        lock: DKEYLock,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            menuai,
            _LOGGER,
            config_entry=entry,
            name=lock.name,
            update_interval=timedelta(seconds=UPDATE_SECONDS),
        )
        self.lock = lock

    async def _async_update_data(self) -> None:
        """Update the device state."""
        try:
            await self.lock.update()
            await self.lock.disconnect()
        except NotAssociated as ex:
            raise ConfigEntryAuthFailed("Not associated") from ex
        except DKEY_EXCEPTIONS as ex:
            raise UpdateFailed(str(ex)) from ex
