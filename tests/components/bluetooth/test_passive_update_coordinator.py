"""Tests for the Bluetooth integration PassiveBluetoothDataUpdateCoordinator."""

from __future__ import annotations

from datetime import timedelta
import logging
import time
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from menuai.components.bluetooth import (
    DOMAIN,
    FALLBACK_MAXIMUM_STALE_ADVERTISEMENT_SECONDS,
    BluetoothChange,
    BluetoothScanningMode,
)
from menuai.components.bluetooth.passive_update_coordinator import (
    PassiveBluetoothCoordinatorEntity,
    PassiveBluetoothDataUpdateCoordinator,
)
from menuai.core import menuai
from menuai.helpers.service_info.bluetooth import BluetoothServiceInfo
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util

from . import (
    inject_bluetooth_service_info,
    patch_all_discovered_devices,
    patch_bluetooth_time,
)

from tests.common import async_fire_time_changed

_LOGGER = logging.getLogger(__name__)


GENERIC_BLUETOOTH_SERVICE_INFO = BluetoothServiceInfo(
    name="Generic",
    address="aa:bb:cc:dd:ee:ff",
    rssi=-95,
    manufacturer_data={
        1: b"\x01\x01\x01\x01\x01\x01\x01\x01",
    },
    service_data={},
    service_uuids=[],
    source="local",
)


class MyCoordinator(PassiveBluetoothDataUpdateCoordinator):
    """An example coordinator that subclasses PassiveBluetoothDataUpdateCoordinator."""

    def __init__(
        self,
        menuai: menuai,
        logger: logging.Logger,
        device_id: str,
        mode: BluetoothScanningMode,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(menuai, logger, device_id, mode)
        self.data: dict[str, Any] = {}

    def _async_handle_bluetooth_event(
        self,
        service_info: BluetoothServiceInfo,
        change: BluetoothChange,
    ) -> None:
        """Handle a Bluetooth event."""
        self.data = {"rssi": service_info.rssi}
        super()._async_handle_bluetooth_event(service_info, change)


@pytest.mark.usefixtures("mock_bleak_scanner_start", "mock_bluetooth_adapters")
async def test_basic_usage(menuai: menuai) -> None:
    """Test basic usage of the PassiveBluetoothDataUpdateCoordinator."""
    await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})
    coordinator = MyCoordinator(
        menuai, _LOGGER, "aa:bb:cc:dd:ee:ff", BluetoothScanningMode.ACTIVE
    )
    assert coordinator.available is False  # no data yet

    mock_listener = MagicMock()
    unregister_listener = coordinator.async_add_listener(mock_listener)

    cancel = coordinator.async_start()

    inject_bluetooth_service_info(menuai, GENERIC_BLUETOOTH_SERVICE_INFO)

    assert len(mock_listener.mock_calls) == 1
    assert coordinator.data == {"rssi": GENERIC_BLUETOOTH_SERVICE_INFO.rssi}
    assert coordinator.available is True

    unregister_listener()
    inject_bluetooth_service_info(menuai, GENERIC_BLUETOOTH_SERVICE_INFO)

    assert len(mock_listener.mock_calls) == 1
    assert coordinator.data == {"rssi": GENERIC_BLUETOOTH_SERVICE_INFO.rssi}
    assert coordinator.available is True
    cancel()


@pytest.mark.usefixtures("mock_bleak_scanner_start", "mock_bluetooth_adapters")
async def test_context_compatiblity_with_data_update_coordinator(
    menuai: menuai,
) -> None:
    """Test contexts can be passed for compatibility with DataUpdateCoordinator."""
    await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})
    coordinator = MyCoordinator(
        menuai, _LOGGER, "aa:bb:cc:dd:ee:ff", BluetoothScanningMode.ACTIVE
    )
    assert coordinator.available is False  # no data yet

    mock_listener = MagicMock()
    coordinator.async_add_listener(mock_listener)

    coordinator.async_start()

    assert not set(coordinator.async_contexts())

    def update_callback1():
        pass

    def update_callback2():
        pass

    unsub1 = coordinator.async_add_listener(update_callback1, 1)
    assert set(coordinator.async_contexts()) == {1}

    unsub2 = coordinator.async_add_listener(update_callback2, 2)
    assert set(coordinator.async_contexts()) == {1, 2}

    unsub1()
    assert set(coordinator.async_contexts()) == {2}

    unsub2()
    assert not set(coordinator.async_contexts())


@pytest.mark.usefixtures("mock_bleak_scanner_start", "mock_bluetooth_adapters")
async def test_unavailable_callbacks_mark_the_coordinator_unavailable(
    menuai: menuai,
) -> None:
    """Test that the coordinator goes unavailable when the bluetooth stack no longer sees the device."""
    start_monotonic = time.monotonic()
    with patch(
        "bleak.BleakScanner.discovered_devices_and_advertisement_data",  # Must patch before we setup
        {"44:44:33:11:23:45": (MagicMock(address="44:44:33:11:23:45"), MagicMock())},
    ):
        await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})
        await menuai.async_block_till_done()
    coordinator = MyCoordinator(
        menuai, _LOGGER, "aa:bb:cc:dd:ee:ff", BluetoothScanningMode.PASSIVE
    )
    assert coordinator.available is False  # no data yet

    mock_listener = MagicMock()
    coordinator.async_add_listener(mock_listener)

    coordinator.async_start()

    assert coordinator.available is False
    inject_bluetooth_service_info(menuai, GENERIC_BLUETOOTH_SERVICE_INFO)
    assert coordinator.available is True

    monotonic_now = start_monotonic + FALLBACK_MAXIMUM_STALE_ADVERTISEMENT_SECONDS + 1

    with (
        patch_bluetooth_time(monotonic_now),
        patch_all_discovered_devices([MagicMock(address="44:44:33:11:23:45")]),
    ):
        async_fire_time_changed(
            menuai,
            dt_util.utcnow()
            + timedelta(seconds=FALLBACK_MAXIMUM_STALE_ADVERTISEMENT_SECONDS + 1),
        )
        await menuai.async_block_till_done()
    assert coordinator.available is False

    inject_bluetooth_service_info(menuai, GENERIC_BLUETOOTH_SERVICE_INFO)
    assert coordinator.available is True

    monotonic_now = start_monotonic + FALLBACK_MAXIMUM_STALE_ADVERTISEMENT_SECONDS + 2

    with (
        patch_bluetooth_time(
            monotonic_now,
        ),
        patch_all_discovered_devices([MagicMock(address="44:44:33:11:23:45")]),
    ):
        async_fire_time_changed(
            menuai,
            dt_util.utcnow()
            + timedelta(seconds=FALLBACK_MAXIMUM_STALE_ADVERTISEMENT_SECONDS + 2),
        )
        await menuai.async_block_till_done()
    assert coordinator.available is False


@pytest.mark.usefixtures("mock_bleak_scanner_start", "mock_bluetooth_adapters")
async def test_passive_bluetooth_coordinator_entity(menuai: menuai) -> None:
    """Test integration of PassiveBluetoothDataUpdateCoordinator with PassiveBluetoothCoordinatorEntity."""
    await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})
    coordinator = MyCoordinator(
        menuai, _LOGGER, "aa:bb:cc:dd:ee:ff", BluetoothScanningMode.ACTIVE
    )
    entity = PassiveBluetoothCoordinatorEntity(coordinator)
    assert entity.available is False

    coordinator.async_start()

    assert coordinator.available is False
    inject_bluetooth_service_info(menuai, GENERIC_BLUETOOTH_SERVICE_INFO)
    assert coordinator.available is True
    entity.menuai = menuai
    await entity.async_update()
    assert entity.available is True
