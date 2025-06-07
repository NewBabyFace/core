"""Coordinator for the venstar component."""

from __future__ import annotations

import asyncio
from datetime import timedelta

from requests import RequestException
from venstarcolortouch import VenstarColorTouch

from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers import update_coordinator

from .const import _LOGGER, DOMAIN, VENSTAR_SLEEP


class VenstarDataUpdateCoordinator(update_coordinator.DataUpdateCoordinator[None]):
    """Class to manage fetching Venstar data."""

    config_entry: ConfigEntry

    def __init__(
        self,
        menuai: menuai,
        config_entry: ConfigEntry,
        venstar_connection: VenstarColorTouch,
    ) -> None:
        """Initialize global Venstar data updater."""
        super().__init__(
            menuai,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=60),
        )
        self.client = venstar_connection
        self.runtimes: list[dict[str, int]] = []

    async def _async_update_data(self) -> None:
        """Update the state."""
        try:
            await self.menuai.async_add_executor_job(self.client.update_info)
        except (OSError, RequestException) as ex:
            raise update_coordinator.UpdateFailed(
                f"Exception during Venstar info update: {ex}"
            ) from ex

        # older venstars sometimes cannot handle rapid sequential connections
        await asyncio.sleep(VENSTAR_SLEEP)

        try:
            await self.menuai.async_add_executor_job(self.client.update_sensors)
        except (OSError, RequestException) as ex:
            raise update_coordinator.UpdateFailed(
                f"Exception during Venstar sensor update: {ex}"
            ) from ex

        # older venstars sometimes cannot handle rapid sequential connections
        await asyncio.sleep(VENSTAR_SLEEP)

        try:
            await self.menuai.async_add_executor_job(self.client.update_alerts)
        except (OSError, RequestException) as ex:
            raise update_coordinator.UpdateFailed(
                f"Exception during Venstar alert update: {ex}"
            ) from ex

        # older venstars sometimes cannot handle rapid sequential connections
        await asyncio.sleep(VENSTAR_SLEEP)

        try:
            self.runtimes = await self.menuai.async_add_executor_job(
                self.client.get_runtimes
            )
        except (OSError, RequestException) as ex:
            raise update_coordinator.UpdateFailed(
                f"Exception during Venstar runtime update: {ex}"
            ) from ex
