"""Test Wallbox Switch component."""

from menuai.const import CONF_UNIT_OF_MEASUREMENT, UnitOfPower
from menuai.core import menuai

from . import setup_integration
from .const import (
    MOCK_SENSOR_CHARGING_POWER_ID,
    MOCK_SENSOR_CHARGING_SPEED_ID,
    MOCK_SENSOR_MAX_AVAILABLE_POWER,
)

from tests.common import MockConfigEntry


async def test_wallbox_sensor_class(
    menuai: menuai, entry: MockConfigEntry
) -> None:
    """Test wallbox sensor class."""

    await setup_integration(menuai, entry)

    state = menuai.states.get(MOCK_SENSOR_CHARGING_POWER_ID)
    assert state.attributes[CONF_UNIT_OF_MEASUREMENT] == UnitOfPower.KILO_WATT
    assert state.name == "Wallbox WallboxName Charging power"

    state = menuai.states.get(MOCK_SENSOR_CHARGING_SPEED_ID)
    assert state.name == "Wallbox WallboxName Charging speed"

    # Test round with precision '0' works
    state = menuai.states.get(MOCK_SENSOR_MAX_AVAILABLE_POWER)
    assert state.state == "25.0"
