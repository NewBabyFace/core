"""Test schlage sensor."""

from menuai.components.sensor import SensorDeviceClass
from menuai.const import PERCENTAGE
from menuai.core import menuai

from . import MockSchlageConfigEntry


async def test_battery_sensor(
    menuai: menuai, mock_added_config_entry: MockSchlageConfigEntry
) -> None:
    """Test the battery sensor."""
    battery_sensor = menuai.states.get("sensor.vault_door_battery")
    assert battery_sensor is not None
    assert battery_sensor.state == "20"
    assert battery_sensor.attributes["unit_of_measurement"] == PERCENTAGE
    assert battery_sensor.attributes["device_class"] == SensorDeviceClass.BATTERY
