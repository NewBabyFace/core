"""The sensor tests for the Nightscout platform."""

from menuai.components.nightscout.const import (
    ATTR_DELTA,
    ATTR_DEVICE,
    ATTR_DIRECTION,
)
from menuai.const import ATTR_DATE, ATTR_ICON, STATE_UNAVAILABLE
from menuai.core import menuai

from . import (
    GLUCOSE_READINGS,
    init_integration,
    init_integration_empty_response,
    init_integration_unavailable,
)


async def test_sensor_state(menuai: menuai) -> None:
    """Test sensor state data."""
    await init_integration(menuai)

    test_glucose_sensor = menuai.states.get("sensor.blood_sugar")
    assert test_glucose_sensor.state == str(
        GLUCOSE_READINGS[0].sgv  # pylint: disable=maybe-no-member
    )


async def test_sensor_error(menuai: menuai) -> None:
    """Test sensor state data."""
    await init_integration_unavailable(menuai)

    test_glucose_sensor = menuai.states.get("sensor.blood_sugar")
    assert test_glucose_sensor.state == STATE_UNAVAILABLE


async def test_sensor_empty_response(menuai: menuai) -> None:
    """Test sensor state data."""
    await init_integration_empty_response(menuai)

    test_glucose_sensor = menuai.states.get("sensor.blood_sugar")
    assert test_glucose_sensor.state == STATE_UNAVAILABLE


async def test_sensor_attributes(menuai: menuai) -> None:
    """Test sensor attributes."""
    await init_integration(menuai)

    test_glucose_sensor = menuai.states.get("sensor.blood_sugar")
    reading = GLUCOSE_READINGS[0]
    assert reading is not None

    attr = test_glucose_sensor.attributes
    assert attr[ATTR_DATE] == reading.date  # pylint: disable=maybe-no-member
    assert attr[ATTR_DELTA] == reading.delta  # pylint: disable=maybe-no-member
    assert attr[ATTR_DEVICE] == reading.device  # pylint: disable=maybe-no-member
    assert attr[ATTR_DIRECTION] == reading.direction  # pylint: disable=maybe-no-member
    assert attr[ATTR_ICON] == "mdi:arrow-bottom-right"
