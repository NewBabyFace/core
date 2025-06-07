"""Coordinator for the Pure Energie integration."""

from __future__ import annotations

from typing import NamedTuple

from gridnet import Device, GridNet, SmartBridge

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_HOST
from menuai.core import menuai
from menuai.helpers.aiohttp_client import async_get_clientsession
from menuai.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, LOGGER, SCAN_INTERVAL

type PureEnergieConfigEntry = ConfigEntry[PureEnergieDataUpdateCoordinator]


class PureEnergieData(NamedTuple):
    """Class for defining data in dict."""

    device: Device
    smartbridge: SmartBridge


class PureEnergieDataUpdateCoordinator(DataUpdateCoordinator[PureEnergieData]):
    """Class to manage fetching Pure Energie data from single eindpoint."""

    config_entry: PureEnergieConfigEntry

    def __init__(
        self,
        menuai: menuai,
        config_entry: PureEnergieConfigEntry,
    ) -> None:
        """Initialize global Pure Energie data updater."""
        super().__init__(
            menuai,
            LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )

        self.gridnet = GridNet(
            self.config_entry.data[CONF_HOST], session=async_get_clientsession(menuai)
        )

    async def _async_update_data(self) -> PureEnergieData:
        """Fetch data from SmartBridge."""
        return PureEnergieData(
            device=await self.gridnet.device(),
            smartbridge=await self.gridnet.smartbridge(),
        )
