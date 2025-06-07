"""Test the ibeacon sensors."""

from datetime import timedelta

import pytest

from menuai.components.bluetooth.const import UNAVAILABLE_TRACK_SECONDS
from menuai.components.ibeacon.const import DOMAIN, UPDATE_INTERVAL
from menuai.components.sensor import ATTR_STATE_CLASS
from menuai.const import (
    ATTR_FRIENDLY_NAME,
    ATTR_UNIT_OF_MEASUREMENT,
    STATE_UNAVAILABLE,
)
from menuai.core import menuai
from menuai.util import dt as dt_util

from . import (
    BLUECHARM_BEACON_SERVICE_INFO,
    BLUECHARM_BEACON_SERVICE_INFO_2,
    BLUECHARM_BLE_DEVICE,
    FEASY_BEACON_BLE_DEVICE,
    FEASY_BEACON_SERVICE_INFO_1,
    FEASY_BEACON_SERVICE_INFO_2,
    NO_NAME_BEACON_SERVICE_INFO,
    bluetooth_service_info_replace as replace,
)

from tests.common import MockConfigEntry, async_fire_time_changed
from tests.components.bluetooth import (
    inject_bluetooth_service_info,
    patch_all_discovered_devices,
)


@pytest.fixture(autouse=True)
def mock_bluetooth(enable_bluetooth: None) -> None:
    """Auto mock bluetooth."""


async def test_sensors_updates_fixed_mac_address(menuai: menuai) -> None:
    """Test creating and updating sensors with a fixed mac address."""
    entry = MockConfigEntry(
        domain=DOMAIN,
    )
    entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    with patch_all_discovered_devices([BLUECHARM_BLE_DEVICE]):
        inject_bluetooth_service_info(menuai, BLUECHARM_BEACON_SERVICE_INFO)
        await menuai.async_block_till_done()

    distance_sensor = menuai.states.get("sensor.bluecharm_177999_8105_estimated_distance")
    distance_attributes = distance_sensor.attributes
    assert distance_sensor.state == "2"
    assert (
        distance_attributes[ATTR_FRIENDLY_NAME]
        == "BlueCharm_177999 8105 Estimated distance"
    )
    assert distance_attributes[ATTR_UNIT_OF_MEASUREMENT] == "m"
    assert distance_attributes[ATTR_STATE_CLASS] == "measurement"

    with patch_all_discovered_devices([BLUECHARM_BLE_DEVICE]):
        inject_bluetooth_service_info(menuai, BLUECHARM_BEACON_SERVICE_INFO_2)
        await menuai.async_block_till_done()

    distance_sensor = menuai.states.get("sensor.bluecharm_177999_8105_estimated_distance")
    distance_attributes = distance_sensor.attributes
    assert distance_sensor.state == "0"
    assert (
        distance_attributes[ATTR_FRIENDLY_NAME]
        == "BlueCharm_177999 8105 Estimated distance"
    )
    assert distance_attributes[ATTR_UNIT_OF_MEASUREMENT] == "m"
    assert distance_attributes[ATTR_STATE_CLASS] == "measurement"

    # Make sure RSSI updates are picked up by the periodic update
    inject_bluetooth_service_info(
        menuai, replace(BLUECHARM_BEACON_SERVICE_INFO_2, rssi=-84)
    )

    # We should not see it right away since the update interval is 60 seconds
    distance_sensor = menuai.states.get("sensor.bluecharm_177999_8105_estimated_distance")
    distance_attributes = distance_sensor.attributes
    assert distance_sensor.state == "0"

    with patch_all_discovered_devices([BLUECHARM_BLE_DEVICE]):
        async_fire_time_changed(
            menuai,
            dt_util.utcnow() + timedelta(seconds=UPDATE_INTERVAL.total_seconds() * 2),
        )
        await menuai.async_block_till_done()

    distance_sensor = menuai.states.get("sensor.bluecharm_177999_8105_estimated_distance")
    distance_attributes = distance_sensor.attributes
    assert distance_sensor.state == "14"
    assert (
        distance_attributes[ATTR_FRIENDLY_NAME]
        == "BlueCharm_177999 8105 Estimated distance"
    )
    assert distance_attributes[ATTR_UNIT_OF_MEASUREMENT] == "m"
    assert distance_attributes[ATTR_STATE_CLASS] == "measurement"

    with patch_all_discovered_devices([]):
        await menuai.async_block_till_done()
        async_fire_time_changed(
            menuai, dt_util.utcnow() + timedelta(seconds=UNAVAILABLE_TRACK_SECONDS * 2)
        )
        await menuai.async_block_till_done()

    distance_sensor = menuai.states.get("sensor.bluecharm_177999_8105_estimated_distance")
    assert distance_sensor.state == STATE_UNAVAILABLE

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()


async def test_sensor_with_no_local_name(menuai: menuai) -> None:
    """Test creating and updating sensors."""
    entry = MockConfigEntry(
        domain=DOMAIN,
    )
    entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    inject_bluetooth_service_info(menuai, NO_NAME_BEACON_SERVICE_INFO)
    await menuai.async_block_till_done()

    assert (
        menuai.states.get(
            "sensor.4e6f4e61_6d65_6172_6d42_6561636f6e73_3838_4949_8105_estimated_distance"
        )
        is not None
    )

    assert await menuai.config_entries.async_unload(entry.entry_id)


async def test_sensor_sees_last_service_info(menuai: menuai) -> None:
    """Test sensors are created from recent history."""
    entry = MockConfigEntry(
        domain=DOMAIN,
    )
    entry.add_to_menuai(menuai)
    inject_bluetooth_service_info(menuai, BLUECHARM_BEACON_SERVICE_INFO)

    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert (
        menuai.states.get("sensor.bluecharm_177999_8105_estimated_distance").state == "2"
    )

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()


async def test_can_unload_and_reload(menuai: menuai) -> None:
    """Test sensors get recreated on unload/setup."""
    entry = MockConfigEntry(
        domain=DOMAIN,
    )
    entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()
    inject_bluetooth_service_info(menuai, BLUECHARM_BEACON_SERVICE_INFO)
    await menuai.async_block_till_done()
    assert (
        menuai.states.get("sensor.bluecharm_177999_8105_estimated_distance").state == "2"
    )

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()
    assert (
        menuai.states.get("sensor.bluecharm_177999_8105_estimated_distance").state
        == STATE_UNAVAILABLE
    )
    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()
    assert (
        menuai.states.get("sensor.bluecharm_177999_8105_estimated_distance").state == "2"
    )


async def test_multiple_uuids_same_beacon(menuai: menuai) -> None:
    """Test a beacon that broadcasts multiple uuids."""
    entry = MockConfigEntry(
        domain=DOMAIN,
    )
    entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    with patch_all_discovered_devices([FEASY_BEACON_BLE_DEVICE]):
        inject_bluetooth_service_info(menuai, FEASY_BEACON_SERVICE_INFO_1)
        await menuai.async_block_till_done()

    distance_sensor = menuai.states.get("sensor.fsc_bp108_eeff_estimated_distance")
    distance_attributes = distance_sensor.attributes
    assert distance_sensor.state == "400"
    assert (
        distance_attributes[ATTR_FRIENDLY_NAME] == "FSC-BP108 EEFF Estimated distance"
    )
    assert distance_attributes[ATTR_UNIT_OF_MEASUREMENT] == "m"
    assert distance_attributes[ATTR_STATE_CLASS] == "measurement"

    with patch_all_discovered_devices([FEASY_BEACON_BLE_DEVICE]):
        inject_bluetooth_service_info(menuai, FEASY_BEACON_SERVICE_INFO_2)
        await menuai.async_block_till_done()

    distance_sensor = menuai.states.get("sensor.fsc_bp108_eeff_estimated_distance_2")
    distance_attributes = distance_sensor.attributes
    assert distance_sensor.state == "0"
    assert (
        distance_attributes[ATTR_FRIENDLY_NAME] == "FSC-BP108 EEFF Estimated distance"
    )
    assert distance_attributes[ATTR_UNIT_OF_MEASUREMENT] == "m"
    assert distance_attributes[ATTR_STATE_CLASS] == "measurement"

    with patch_all_discovered_devices([FEASY_BEACON_BLE_DEVICE]):
        inject_bluetooth_service_info(menuai, FEASY_BEACON_SERVICE_INFO_1)
        await menuai.async_block_till_done()

    distance_sensor = menuai.states.get("sensor.fsc_bp108_eeff_estimated_distance")
    distance_attributes = distance_sensor.attributes
    assert distance_sensor.state == "400"
    assert (
        distance_attributes[ATTR_FRIENDLY_NAME] == "FSC-BP108 EEFF Estimated distance"
    )
    assert distance_attributes[ATTR_UNIT_OF_MEASUREMENT] == "m"
    assert distance_attributes[ATTR_STATE_CLASS] == "measurement"

    distance_sensor = menuai.states.get("sensor.fsc_bp108_eeff_estimated_distance_2")
    distance_attributes = distance_sensor.attributes
    assert distance_sensor.state == "0"
    assert (
        distance_attributes[ATTR_FRIENDLY_NAME] == "FSC-BP108 EEFF Estimated distance"
    )
    assert distance_attributes[ATTR_UNIT_OF_MEASUREMENT] == "m"
    assert distance_attributes[ATTR_STATE_CLASS] == "measurement"
