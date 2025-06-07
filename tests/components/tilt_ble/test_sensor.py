"""Test the Tilt Hydrometer BLE sensors."""

from __future__ import annotations

from menuai.components.sensor import ATTR_STATE_CLASS, async_rounded_state
from menuai.components.tilt_ble.const import DOMAIN
from menuai.const import ATTR_FRIENDLY_NAME, ATTR_UNIT_OF_MEASUREMENT
from menuai.core import menuai

from . import TILT_GREEN_SERVICE_INFO

from tests.common import MockConfigEntry
from tests.components.bluetooth import inject_bluetooth_service_info


async def test_sensors(menuai: menuai) -> None:
    """Test setting up creates the sensors."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="F6:0F:28:F2:1F:CB",
    )
    entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert len(menuai.states.async_all()) == 0
    inject_bluetooth_service_info(menuai, TILT_GREEN_SERVICE_INFO)
    await menuai.async_block_till_done()
    assert (
        len(menuai.states.async_all()) >= 2
    )  # may trigger ibeacon integration as well since tilt uses ibeacon

    temp_sensor = menuai.states.get("sensor.tilt_green_temperature")
    assert temp_sensor is not None

    temp_sensor_attribtes = temp_sensor.attributes
    assert (
        async_rounded_state(menuai, "sensor.tilt_green_temperature", temp_sensor)
        == "21.1"
    )
    assert temp_sensor_attribtes[ATTR_FRIENDLY_NAME] == "Tilt Green Temperature"
    assert temp_sensor_attribtes[ATTR_UNIT_OF_MEASUREMENT] == "°C"
    assert temp_sensor_attribtes[ATTR_STATE_CLASS] == "measurement"

    temp_sensor = menuai.states.get("sensor.tilt_green_specific_gravity")
    assert temp_sensor is not None

    temp_sensor_attribtes = temp_sensor.attributes
    assert temp_sensor.state == "1.003"
    assert temp_sensor_attribtes[ATTR_FRIENDLY_NAME] == "Tilt Green Specific Gravity"
    assert temp_sensor_attribtes[ATTR_STATE_CLASS] == "measurement"

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()
