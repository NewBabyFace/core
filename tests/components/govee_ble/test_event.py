"""Test the Govee BLE events."""

from menuai.components.govee_ble.const import CONF_DEVICE_TYPE, DOMAIN
from menuai.const import STATE_UNKNOWN
from menuai.core import menuai

from . import (
    GV5121_MOTION_SERVICE_INFO,
    GV5121_MOTION_SERVICE_INFO_2,
    GV5125_BUTTON_0_SERVICE_INFO,
    GV5125_BUTTON_1_SERVICE_INFO,
    GVH5124_2_SERVICE_INFO,
    GVH5124_SERVICE_INFO,
)

from tests.common import MockConfigEntry
from tests.components.bluetooth import inject_bluetooth_service_info


async def test_motion_sensor(menuai: menuai) -> None:
    """Test setting up creates the motion sensor."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=GV5121_MOTION_SERVICE_INFO.address,
        data={CONF_DEVICE_TYPE: "H5121"},
    )
    entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert len(menuai.states.async_all()) == 1
    inject_bluetooth_service_info(menuai, GV5121_MOTION_SERVICE_INFO)
    await menuai.async_block_till_done()
    assert len(menuai.states.async_all()) == 2

    motion_sensor = menuai.states.get("event.h5121_motion")
    first_time = motion_sensor.state
    assert motion_sensor.state != STATE_UNKNOWN

    inject_bluetooth_service_info(menuai, GV5121_MOTION_SERVICE_INFO_2)
    await menuai.async_block_till_done()

    motion_sensor = menuai.states.get("event.h5121_motion")
    assert motion_sensor.state != first_time
    assert motion_sensor.state != STATE_UNKNOWN
    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()


async def test_button(menuai: menuai) -> None:
    """Test setting up creates the buttons."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=GV5125_BUTTON_1_SERVICE_INFO.address,
        data={CONF_DEVICE_TYPE: "H5125"},
    )
    entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert len(menuai.states.async_all()) == 6
    inject_bluetooth_service_info(menuai, GV5125_BUTTON_1_SERVICE_INFO)
    await menuai.async_block_till_done()

    button_1 = menuai.states.get("event.h5125_button_1")
    assert button_1.state == STATE_UNKNOWN

    inject_bluetooth_service_info(menuai, GV5125_BUTTON_0_SERVICE_INFO)
    await menuai.async_block_till_done()
    button_1 = menuai.states.get("event.h5125_button_1")
    assert button_1.state != STATE_UNKNOWN
    assert len(menuai.states.async_all()) == 7

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()


async def test_vibration_sensor(menuai: menuai) -> None:
    """Test setting up creates the vibration sensor."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=GVH5124_SERVICE_INFO.address,
        data={CONF_DEVICE_TYPE: "H5124"},
    )
    entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert len(menuai.states.async_all()) == 1
    inject_bluetooth_service_info(menuai, GVH5124_SERVICE_INFO)
    await menuai.async_block_till_done()
    assert len(menuai.states.async_all()) == 2

    motion_sensor = menuai.states.get("event.h5124_vibration")
    first_time = motion_sensor.state
    assert motion_sensor.state != STATE_UNKNOWN

    inject_bluetooth_service_info(menuai, GVH5124_2_SERVICE_INFO)
    await menuai.async_block_till_done()

    motion_sensor = menuai.states.get("event.h5124_vibration")
    assert motion_sensor.state != first_time
    assert motion_sensor.state != STATE_UNKNOWN
    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()
