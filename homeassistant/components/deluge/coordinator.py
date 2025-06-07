"""Data update coordinator for the Deluge integration."""

from __future__ import annotations

from datetime import timedelta
from ssl import SSLError
from typing import Any

from deluge_client.client import DelugeRPCClient, FailedToReconnectException

from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryAuthFailed
from menuai.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import LOGGER, DelugeGetSessionStatusKeys

type DelugeConfigEntry = ConfigEntry[DelugeDataUpdateCoordinator]


class DelugeDataUpdateCoordinator(
    DataUpdateCoordinator[dict[Platform, dict[str, Any]]]
):
    """Data update coordinator for the Deluge integration."""

    config_entry: DelugeConfigEntry

    def __init__(
        self, menuai: menuai, api: DelugeRPCClient, entry: DelugeConfigEntry
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            menuai=menuai,
            logger=LOGGER,
            config_entry=entry,
            name=entry.title,
            update_interval=timedelta(seconds=30),
        )
        self.api = api

    async def _async_update_data(self) -> dict[Platform, dict[str, Any]]:
        """Get the latest data from Deluge and updates the state."""
        data = {}
        try:
            _data = await self.menuai.async_add_executor_job(
                self.api.call,
                "core.get_session_status",
                [iter_member.value for iter_member in list(DelugeGetSessionStatusKeys)],
            )
            data[Platform.SENSOR] = {k.decode(): v for k, v in _data.items()}
            data[Platform.SWITCH] = await self.menuai.async_add_executor_job(
                self.api.call, "core.get_torrents_status", {}, ["paused"]
            )
        except (
            ConnectionRefusedError,
            TimeoutError,
            SSLError,
            FailedToReconnectException,
        ) as ex:
            raise UpdateFailed(f"Connection to Deluge Daemon Lost: {ex}") from ex
        except Exception as ex:
            if type(ex).__name__ == "BadLoginError":
                raise ConfigEntryAuthFailed(
                    "Credentials for Deluge client are not valid"
                ) from ex
            LOGGER.error("Unknown error connecting to Deluge: %s", ex)
            raise
        return data
