"""Test Roborock Binary Sensor."""

import pytest

from menuai.const import Platform
from menuai.core import menuai

from tests.common import MockConfigEntry


@pytest.fixture
def platforms() -> list[Platform]:
    """Fixture to set platforms used in the test."""
    return [Platform.BINARY_SENSOR]


async def test_binary_sensors(
    menuai: menuai, setup_entry: MockConfigEntry
) -> None:
    """Test binary sensors and check test values are correctly set."""
    assert len(menuai.states.async_all("binary_sensor")) == 10
    assert menuai.states.get("binary_sensor.roborock_s7_maxv_mop_attached").state == "on"
    assert (
        menuai.states.get("binary_sensor.roborock_s7_maxv_water_box_attached").state
        == "on"
    )
    assert (
        menuai.states.get("binary_sensor.roborock_s7_maxv_water_shortage").state == "off"
    )
    assert menuai.states.get("binary_sensor.roborock_s7_maxv_cleaning").state == "off"
    assert menuai.states.get("binary_sensor.roborock_s7_maxv_charging").state == "on"
