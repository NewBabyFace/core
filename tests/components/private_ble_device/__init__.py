"""Tests for private_ble_device."""

from datetime import timedelta
import time

from home_assistant_bluetooth import BluetoothServiceInfoBleak

from menuai.components.private_ble_device.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai
from menuai.util import dt as dt_util

from tests.common import MockConfigEntry, async_fire_time_changed
from tests.components.bluetooth import (
    generate_advertisement_data,
    generate_ble_device,
    inject_bluetooth_service_info_bleak,
    patch_bluetooth_time,
)

MAC_RPA_VALID_1 = "40:01:02:0a:c4:a6"
MAC_RPA_VALID_2 = "40:02:03:d2:74:ce"
MAC_RPA_INVALID = "40:00:00:d2:74:ce"
MAC_STATIC = "00:01:ff:a0:3a:76"

DUMMY_IRK = "00000000000000000000000000000000"


async def async_mock_config_entry(menuai: menuai, irk: str = DUMMY_IRK) -> None:
    """Create a test device for a dummy IRK."""
    entry = MockConfigEntry(
        version=1,
        domain=DOMAIN,
        entry_id=irk,
        data={"irk": irk},
        title="Private BLE Device 000000",
    )
    entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.LOADED
    await menuai.async_block_till_done()


async def async_inject_broadcast(
    menuai: menuai,
    mac: str = MAC_RPA_VALID_1,
    mfr_data: bytes = b"",
    broadcast_time: float | None = None,
) -> None:
    """Inject an advertisement."""
    inject_bluetooth_service_info_bleak(
        menuai,
        BluetoothServiceInfoBleak(
            name="Test Test Test",
            address=mac,
            rssi=-63,
            service_data={},
            manufacturer_data={1: mfr_data},
            service_uuids=[],
            source="local",
            device=generate_ble_device(mac, "Test Test Test"),
            advertisement=generate_advertisement_data(local_name="Not it"),
            time=broadcast_time or time.monotonic(),
            connectable=False,
            tx_power=-127,
        ),
    )
    await menuai.async_block_till_done()


async def async_move_time_forwards(menuai: menuai, offset: float):
    """Mock time advancing from now to now+offset."""
    with patch_bluetooth_time(
        time.monotonic() + offset,
    ):
        async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(seconds=offset))
        await menuai.async_block_till_done()
