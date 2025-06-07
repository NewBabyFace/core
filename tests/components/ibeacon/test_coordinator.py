"""Test the ibeacon sensors."""

from datetime import timedelta
import time

import pytest

from menuai.components.bluetooth import (
    FALLBACK_MAXIMUM_STALE_ADVERTISEMENT_SECONDS,
)
from menuai.components.ibeacon.const import (
    ATTR_SOURCE,
    CONF_ALLOW_NAMELESS_UUIDS,
    DOMAIN,
    UPDATE_INTERVAL,
)
from menuai.const import STATE_HOME
from menuai.core import menuai
from menuai.helpers.service_info.bluetooth import BluetoothServiceInfo
from menuai.util import dt as dt_util

from . import (
    BLUECHARM_BEACON_SERVICE_INFO,
    BLUECHARM_BEACON_SERVICE_INFO_2,
    BLUECHARM_BEACON_SERVICE_INFO_DBUS,
    TESLA_TRANSIENT,
    TESLA_TRANSIENT_BLE_DEVICE,
    bluetooth_service_info_replace as replace,
)

from tests.common import MockConfigEntry, async_fire_time_changed
from tests.components.bluetooth import (
    generate_advertisement_data,
    generate_ble_device,
    inject_advertisement_with_time_and_source_connectable,
    inject_bluetooth_service_info,
    patch_all_discovered_devices,
    patch_bluetooth_time,
)


@pytest.fixture(autouse=True)
def mock_bluetooth(enable_bluetooth: None) -> None:
    """Auto mock bluetooth."""


async def test_many_groups_same_address_ignored(menuai: menuai) -> None:
    """Test the different uuid, major, minor from many addresses removes all associated entities."""
    entry = MockConfigEntry(
        domain=DOMAIN,
    )
    entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    inject_bluetooth_service_info(menuai, BLUECHARM_BEACON_SERVICE_INFO)
    await menuai.async_block_till_done()

    assert (
        menuai.states.get("sensor.bluecharm_177999_8105_estimated_distance") is not None
    )

    for i in range(12):
        service_info = BluetoothServiceInfo(
            name="BlueCharm_177999",
            address="61DE521B-F0BF-9F44-64D4-75BBE1738105",
            rssi=-63,
            service_data={},
            manufacturer_data={
                76: b"\x02\x15BlueCharmBeacons" + bytearray([i]) + b"\xfe\x13U\xc5"
            },
            service_uuids=[],
            source="local",
        )
        inject_bluetooth_service_info(menuai, service_info)

    await menuai.async_block_till_done()
    assert menuai.states.get("sensor.bluecharm_177999_8105_estimated_distance") is None


async def test_ignore_not_ibeacons(menuai: menuai) -> None:
    """Test we ignore non-ibeacon data."""
    entry = MockConfigEntry(
        domain=DOMAIN,
    )
    entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    before_entity_count = len(menuai.states.async_entity_ids())
    inject_bluetooth_service_info(
        menuai,
        replace(
            BLUECHARM_BEACON_SERVICE_INFO, manufacturer_data={76: b"\x02\x15invalid"}
        ),
    )
    await menuai.async_block_till_done()
    assert len(menuai.states.async_entity_ids()) == before_entity_count


async def test_ignore_no_name_but_create_if_set_later(menuai: menuai) -> None:
    """Test we ignore devices with no name but create it if it set set later."""
    entry = MockConfigEntry(
        domain=DOMAIN,
    )
    entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    before_entity_count = len(menuai.states.async_entity_ids())
    inject_bluetooth_service_info(
        menuai,
        replace(BLUECHARM_BEACON_SERVICE_INFO, name=None),
    )
    await menuai.async_block_till_done()
    assert len(menuai.states.async_entity_ids()) == before_entity_count

    inject_bluetooth_service_info(
        menuai,
        replace(
            BLUECHARM_BEACON_SERVICE_INFO,
            service_data={
                "00002080-0000-1000-8000-00805f9b34fb": b"j\x0c\x0e\xfe\x13U",
                "0000feaa-0000-1000-8000-00805f9b34fb": (
                    b" \x00\x0c\x00\x1c\x00\x00\x00\x06h\x00\x008\x10"
                ),
            },
        ),
    )
    await menuai.async_block_till_done()
    assert len(menuai.states.async_entity_ids()) > before_entity_count


async def test_ignore_default_name(menuai: menuai) -> None:
    """Test we ignore devices with default name."""
    entry = MockConfigEntry(
        domain=DOMAIN,
    )
    entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    before_entity_count = len(menuai.states.async_entity_ids())
    inject_bluetooth_service_info(
        menuai,
        replace(
            BLUECHARM_BEACON_SERVICE_INFO_DBUS,
            name=BLUECHARM_BEACON_SERVICE_INFO_DBUS.address,
        ),
    )
    await menuai.async_block_till_done()
    assert len(menuai.states.async_entity_ids()) == before_entity_count


async def test_default_name_allowlisted(menuai: menuai) -> None:
    """Test we do NOT ignore beacons with default device name but allowlisted UUID."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        options={CONF_ALLOW_NAMELESS_UUIDS: ["426c7565-4368-6172-6d42-6561636f6e73"]},
    )
    entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    before_entity_count = len(menuai.states.async_entity_ids())
    inject_bluetooth_service_info(
        menuai,
        replace(
            BLUECHARM_BEACON_SERVICE_INFO_DBUS,
            name=BLUECHARM_BEACON_SERVICE_INFO_DBUS.address,
        ),
    )
    await menuai.async_block_till_done()
    assert len(menuai.states.async_entity_ids()) > before_entity_count


async def test_default_name_allowlisted_restore(menuai: menuai) -> None:
    """Test that ignored nameless iBeacons are restored when allowlist entry is added."""
    entry = MockConfigEntry(
        domain=DOMAIN,
    )
    entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    before_entity_count = len(menuai.states.async_entity_ids())
    inject_bluetooth_service_info(
        menuai,
        replace(
            BLUECHARM_BEACON_SERVICE_INFO_DBUS,
            name=BLUECHARM_BEACON_SERVICE_INFO_DBUS.address,
        ),
    )
    await menuai.async_block_till_done()
    assert len(menuai.states.async_entity_ids()) == before_entity_count

    result = await menuai.config_entries.options.async_init(entry.entry_id)
    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"new_uuid": "426c7565-4368-6172-6d42-6561636f6e73"},
    )

    await menuai.async_block_till_done()
    assert len(menuai.states.async_entity_ids()) > before_entity_count


async def test_default_name_allowlisted_restore_late(menuai: menuai) -> None:
    """Test that allowlisting an ignored but no longer advertised nameless iBeacon has no effect."""
    start_monotonic = time.monotonic()

    entry = MockConfigEntry(
        domain=DOMAIN,
    )
    entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    before_entity_count = len(menuai.states.async_entity_ids())
    inject_bluetooth_service_info(
        menuai,
        replace(
            BLUECHARM_BEACON_SERVICE_INFO_DBUS,
            name=BLUECHARM_BEACON_SERVICE_INFO_DBUS.address,
        ),
    )
    await menuai.async_block_till_done()
    assert len(menuai.states.async_entity_ids()) == before_entity_count

    # Fastforward time until the device is no longer advertised
    monotonic_now = start_monotonic + FALLBACK_MAXIMUM_STALE_ADVERTISEMENT_SECONDS + 1

    with (
        patch_bluetooth_time(
            monotonic_now,
        ),
        patch_all_discovered_devices([]),
    ):
        async_fire_time_changed(
            menuai,
            dt_util.utcnow()
            + timedelta(seconds=FALLBACK_MAXIMUM_STALE_ADVERTISEMENT_SECONDS + 1),
        )
        await menuai.async_block_till_done()

    result = await menuai.config_entries.options.async_init(entry.entry_id)
    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"new_uuid": "426c7565-4368-6172-6d42-6561636f6e73"},
    )

    await menuai.async_block_till_done()
    assert len(menuai.states.async_entity_ids()) == before_entity_count


async def test_rotating_major_minor_and_mac_with_name(menuai: menuai) -> None:
    """Test the different uuid, major, minor from many addresses removes all associated entities."""
    entry = MockConfigEntry(
        domain=DOMAIN,
    )
    entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()
    before_entity_count = len(menuai.states.async_entity_ids("device_tracker"))

    for i in range(100):
        service_info = BluetoothServiceInfo(
            name="BlueCharm_177999",
            address=f"AA:BB:CC:DD:EE:{i:02X}",
            rssi=-63,
            service_data={},
            manufacturer_data={
                76: b"\x02\x15BlueCharmBeacons"
                + bytearray([i])
                + b"\xfe"
                + bytearray([i])
                + b"U\xc5"
            },
            service_uuids=[],
            source="local",
        )
        inject_bluetooth_service_info(menuai, service_info)
        await menuai.async_block_till_done()
    await menuai.async_block_till_done()
    await menuai.async_block_till_done()

    assert len(menuai.states.async_entity_ids("device_tracker")) == before_entity_count


async def test_rotating_major_minor_and_mac_no_name(menuai: menuai) -> None:
    """Test no-name devices with different uuid, major, minor from many addresses removes all associated entities."""
    entry = MockConfigEntry(
        domain=DOMAIN,
    )
    entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()
    before_entity_count = len(menuai.states.async_entity_ids("device_tracker"))

    for i in range(51):
        service_info = BluetoothServiceInfo(
            name=f"AA:BB:CC:DD:EE:{i:02X}",
            address=f"AA:BB:CC:DD:EE:{i:02X}",
            rssi=-63,
            service_data={},
            manufacturer_data={
                76: b"\x02\x15BlueCharmBeacons"
                + bytearray([i])
                + b"\xfe"
                + bytearray([i])
                + b"U\xc5"
            },
            service_uuids=[],
            source="local",
        )
        inject_bluetooth_service_info(menuai, service_info)
        await menuai.async_block_till_done()
    await menuai.async_block_till_done()
    await menuai.async_block_till_done()

    assert len(menuai.states.async_entity_ids("device_tracker")) == before_entity_count


async def test_ignore_transient_devices_unless_we_see_them_a_few_times(
    menuai: menuai,
) -> None:
    """Test we ignore transient devices unless we see them a few times."""
    entry = MockConfigEntry(
        domain=DOMAIN,
    )
    entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    before_entity_count = len(menuai.states.async_entity_ids())
    inject_bluetooth_service_info(
        menuai,
        TESLA_TRANSIENT,
    )
    await menuai.async_block_till_done()
    assert len(menuai.states.async_entity_ids()) == before_entity_count

    with patch_all_discovered_devices([TESLA_TRANSIENT_BLE_DEVICE]):
        async_fire_time_changed(
            menuai,
            dt_util.utcnow() + timedelta(seconds=UPDATE_INTERVAL.total_seconds() * 2),
        )
        await menuai.async_block_till_done()

    assert len(menuai.states.async_entity_ids()) == before_entity_count

    for i in range(3, 17):
        with patch_all_discovered_devices([TESLA_TRANSIENT_BLE_DEVICE]):
            async_fire_time_changed(
                menuai,
                dt_util.utcnow()
                + timedelta(seconds=UPDATE_INTERVAL.total_seconds() * 2 * i),
            )
            await menuai.async_block_till_done()

    assert len(menuai.states.async_entity_ids()) > before_entity_count

    assert menuai.states.get("device_tracker.s6da7c9389bd5452cc_cccc").state == STATE_HOME

    await menuai.config_entries.async_reload(entry.entry_id)

    await menuai.async_block_till_done()
    assert menuai.states.get("device_tracker.s6da7c9389bd5452cc_cccc").state == STATE_HOME


async def test_changing_source_attribute(menuai: menuai) -> None:
    """Test update of the source attribute."""
    entry = MockConfigEntry(
        domain=DOMAIN,
    )
    entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    now = time.monotonic()
    info = BLUECHARM_BEACON_SERVICE_INFO_2
    device = generate_ble_device(
        address=info.address,
        name=info.name,
        details={},
    )
    advertisement_data = generate_advertisement_data(
        local_name=info.name,
        manufacturer_data=info.manufacturer_data,
        service_data=info.service_data,
        service_uuids=info.service_uuids,
        rssi=info.rssi,
    )

    inject_advertisement_with_time_and_source_connectable(
        menuai,
        device,
        advertisement_data,
        now,
        "local",
        True,
    )
    await menuai.async_block_till_done()

    attributes = menuai.states.get(
        "sensor.bluecharm_177999_8105_estimated_distance"
    ).attributes
    assert attributes[ATTR_SOURCE] == "local"

    inject_advertisement_with_time_and_source_connectable(
        menuai,
        device,
        advertisement_data,
        now,
        "proxy",
        True,
    )
    await menuai.async_block_till_done()
    with patch_all_discovered_devices([BLUECHARM_BEACON_SERVICE_INFO_2]):
        async_fire_time_changed(
            menuai,
            dt_util.utcnow() + timedelta(seconds=UPDATE_INTERVAL.total_seconds() * 2),
        )
        await menuai.async_block_till_done()

    attributes = menuai.states.get(
        "sensor.bluecharm_177999_8105_estimated_distance"
    ).attributes
    assert attributes[ATTR_SOURCE] == "proxy"
