"""Test the Govee BLE sensors."""

from datetime import timedelta
import time

from menuai.components.bluetooth import (
    FALLBACK_MAXIMUM_STALE_ADVERTISEMENT_SECONDS,
)
from menuai.components.govee_ble.const import DOMAIN
from menuai.components.sensor import ATTR_STATE_CLASS
from menuai.const import (
    ATTR_FRIENDLY_NAME,
    ATTR_UNIT_OF_MEASUREMENT,
    STATE_UNAVAILABLE,
)
from menuai.core import menuai
from menuai.util import dt as dt_util

from . import (
    GVH5075_SERVICE_INFO,
    GVH5106_SERVICE_INFO,
    GVH5178_PRIMARY_SERVICE_INFO,
    GVH5178_REMOTE_SERVICE_INFO,
    GVH5178_SERVICE_INFO_ERROR,
)

from tests.common import MockConfigEntry, async_fire_time_changed
from tests.components.bluetooth import (
    inject_bluetooth_service_info,
    patch_all_discovered_devices,
    patch_bluetooth_time,
)


async def test_sensors(menuai: menuai) -> None:
    """Test setting up creates the sensors."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="61DE521B-F0BF-9F44-64D4-75BBE1738105",
    )
    entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert len(menuai.states.async_all()) == 0
    inject_bluetooth_service_info(menuai, GVH5075_SERVICE_INFO)
    await menuai.async_block_till_done()
    assert len(menuai.states.async_all()) == 3

    temp_sensor = menuai.states.get("sensor.h5075_2762_temperature")
    temp_sensor_attribtes = temp_sensor.attributes
    assert temp_sensor.state == "21.3"
    assert temp_sensor_attribtes[ATTR_FRIENDLY_NAME] == "H5075 2762 Temperature"
    assert temp_sensor_attribtes[ATTR_UNIT_OF_MEASUREMENT] == "°C"
    assert temp_sensor_attribtes[ATTR_STATE_CLASS] == "measurement"

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()


async def test_gvh5178_error(menuai: menuai) -> None:
    """Test H5178 Remote in error marks state as unavailable."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="A4:C1:38:75:2B:C8",
    )
    entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert len(menuai.states.async_all()) == 0
    inject_bluetooth_service_info(menuai, GVH5178_SERVICE_INFO_ERROR)
    await menuai.async_block_till_done()
    assert len(menuai.states.async_all()) == 3

    temp_sensor = menuai.states.get("sensor.b51782bc8_remote_temperature")
    assert temp_sensor.state == STATE_UNAVAILABLE

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()


async def test_gvh5178_multi_sensor(menuai: menuai) -> None:
    """Test H5178 with a primary and remote sensor.

    The gateway sensor is responsible for broadcasting the state for
    all sensors and it does so in many advertisements. We want
    all the connected devices to stay available when the gateway
    sensor is available.
    """
    start_monotonic = time.monotonic()
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="A4:C1:38:75:2B:C8",
    )
    entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert len(menuai.states.async_all()) == 0
    inject_bluetooth_service_info(menuai, GVH5178_REMOTE_SERVICE_INFO)
    await menuai.async_block_till_done()
    assert len(menuai.states.async_all()) == 3

    temp_sensor = menuai.states.get("sensor.b51782bc8_remote_temperature")
    assert temp_sensor.state == "1.0"

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()

    # Fastforward time without BLE advertisements
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

    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    temp_sensor = menuai.states.get("sensor.b51782bc8_remote_temperature")
    assert temp_sensor.state == STATE_UNAVAILABLE

    inject_bluetooth_service_info(menuai, GVH5178_PRIMARY_SERVICE_INFO)
    await menuai.async_block_till_done()

    temp_sensor = menuai.states.get("sensor.b51782bc8_remote_temperature")
    assert temp_sensor.state == "1.0"

    primary_temp_sensor = menuai.states.get("sensor.b51782bc8_primary_temperature")
    assert primary_temp_sensor.state == "1.0"

    # Fastforward time without BLE advertisements
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

    temp_sensor = menuai.states.get("sensor.b51782bc8_remote_temperature")
    assert temp_sensor.state == STATE_UNAVAILABLE

    primary_temp_sensor = menuai.states.get("sensor.b51782bc8_primary_temperature")
    assert primary_temp_sensor.state == STATE_UNAVAILABLE


async def test_gvh5106(menuai: menuai) -> None:
    """Test setting up creates the sensors for a device with PM25."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="CC:32:37:35:4E:05",
    )
    entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert len(menuai.states.async_all()) == 0
    inject_bluetooth_service_info(menuai, GVH5106_SERVICE_INFO)
    await menuai.async_block_till_done()
    assert len(menuai.states.async_all()) == 3

    pm25_sensor = menuai.states.get("sensor.h5106_4e05_pm25")
    pm25_sensor_attributes = pm25_sensor.attributes
    assert pm25_sensor.state == "0"
    assert pm25_sensor_attributes[ATTR_FRIENDLY_NAME] == "H5106 4E05 Pm25"
    assert pm25_sensor_attributes[ATTR_UNIT_OF_MEASUREMENT] == "µg/m³"
    assert pm25_sensor_attributes[ATTR_STATE_CLASS] == "measurement"

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()
