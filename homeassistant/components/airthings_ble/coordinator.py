"""The Airthings BLE integration."""

from __future__ import annotations

from datetime import timedelta
import logging

from airthings_ble import AirthingsBluetoothDeviceData, AirthingsDevice
from bleak.backends.device import BLEDevice
from bleak_retry_connector import close_stale_connections_by_address

from menuai.components import bluetooth
from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from menuai.util.unit_system import METRIC_SYSTEM

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

type AirthingsBLEConfigEntry = ConfigEntry[AirthingsBLEDataUpdateCoordinator]


class AirthingsBLEDataUpdateCoordinator(DataUpdateCoordinator[AirthingsDevice]):
    """Class to manage fetching Airthings BLE data."""

    ble_device: BLEDevice
    config_entry: AirthingsBLEConfigEntry

    def __init__(self, menuai: menuai, entry: AirthingsBLEConfigEntry) -> None:
        """Initialize the coordinator."""
        self.airthings = AirthingsBluetoothDeviceData(
            _LOGGER, menuai.config.units is METRIC_SYSTEM
        )
        super().__init__(
            menuai,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_setup(self) -> None:
        """Set up the coordinator."""
        address = self.config_entry.unique_id

        assert address is not None

        await close_stale_connections_by_address(address)

        ble_device = bluetooth.async_ble_device_from_address(self.menuai, address)

        if not ble_device:
            raise ConfigEntryNotReady(
                f"Could not find Airthings device with address {address}"
            )
        self.ble_device = ble_device

    async def _async_update_data(self) -> AirthingsDevice:
        """Get data from Airthings BLE."""
        try:
            data = await self.airthings.update_device(self.ble_device)
        except Exception as err:
            raise UpdateFailed(f"Unable to fetch data: {err}") from err

        return data
