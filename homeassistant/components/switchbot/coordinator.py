"""Provides the switchbot DataUpdateCoordinator."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import TYPE_CHECKING

import switchbot
from switchbot import SwitchbotModel

from menuai.components import bluetooth
from menuai.components.bluetooth.active_update_coordinator import (
    ActiveBluetoothDataUpdateCoordinator,
)
from menuai.config_entries import ConfigEntry
from menuai.core import CoreState, menuai, callback

if TYPE_CHECKING:
    from bleak.backends.device import BLEDevice


_LOGGER = logging.getLogger(__name__)

DEVICE_STARTUP_TIMEOUT = 30

type SwitchbotConfigEntry = ConfigEntry[SwitchbotDataUpdateCoordinator]


class SwitchbotDataUpdateCoordinator(ActiveBluetoothDataUpdateCoordinator[None]):
    """Class to manage fetching switchbot data."""

    def __init__(
        self,
        menuai: menuai,
        logger: logging.Logger,
        ble_device: BLEDevice,
        device: switchbot.SwitchbotDevice,
        base_unique_id: str,
        device_name: str,
        connectable: bool,
        model: SwitchbotModel,
    ) -> None:
        """Initialize global switchbot data updater."""
        super().__init__(
            menuai=menuai,
            logger=logger,
            address=ble_device.address,
            needs_poll_method=self._needs_poll,
            poll_method=self._async_update,
            mode=bluetooth.BluetoothScanningMode.ACTIVE,
            connectable=connectable,
        )
        self.ble_device = ble_device
        self.device = device
        self.device_name = device_name
        self.base_unique_id = base_unique_id
        self.model = model
        self._ready_event = asyncio.Event()
        self._was_unavailable = True

    @callback
    def _needs_poll(
        self,
        service_info: bluetooth.BluetoothServiceInfoBleak,
        seconds_since_last_poll: float | None,
    ) -> bool:
        # Only poll if menuai is running, we need to poll,
        # and we actually have a way to connect to the device
        return (
            self.menuai.state is CoreState.running
            and self.device.poll_needed(seconds_since_last_poll)
            and bool(
                bluetooth.async_ble_device_from_address(
                    self.menuai, service_info.device.address, connectable=True
                )
            )
        )

    async def _async_update(
        self, service_info: bluetooth.BluetoothServiceInfoBleak
    ) -> None:
        """Poll the device."""
        await self.device.update()

    @callback
    def _async_handle_unavailable(
        self, service_info: bluetooth.BluetoothServiceInfoBleak
    ) -> None:
        """Handle the device going unavailable."""
        super()._async_handle_unavailable(service_info)
        self._was_unavailable = True
        _LOGGER.info("Device %s is unavailable", self.device_name)

    @callback
    def _async_handle_bluetooth_event(
        self,
        service_info: bluetooth.BluetoothServiceInfoBleak,
        change: bluetooth.BluetoothChange,
    ) -> None:
        """Handle a Bluetooth event."""
        self.ble_device = service_info.device
        if not (
            adv := switchbot.parse_advertisement_data(
                service_info.device, service_info.advertisement, self.model
            )
        ):
            return
        if "modelName" in adv.data:
            self._ready_event.set()
        _LOGGER.debug(
            "%s: Switchbot data: %s", self.ble_device.address, self.device.data
        )
        if not self.device.advertisement_changed(adv) and not self._was_unavailable:
            return
        self._was_unavailable = False
        _LOGGER.info("Device %s is online", self.device_name)
        self.device.update_from_advertisement(adv)
        super()._async_handle_bluetooth_event(service_info, change)

    async def async_wait_ready(self) -> bool:
        """Wait for the device to be ready."""
        with contextlib.suppress(TimeoutError):
            async with asyncio.timeout(DEVICE_STARTUP_TIMEOUT):
                await self._ready_event.wait()
                return True
        return False
