"""Tests for binary sensors."""

from menuai.core import menuai

from .conftest import (
    EntityAndExpectedValues,
    _test_sensors,
    get_lifetime_mock,
    get_vitals_mock,
)


async def test_sensors(menuai: menuai) -> None:
    """Test all binary sensors."""

    entity_and_expected_values = [
        EntityAndExpectedValues(
            "binary_sensor.tesla_wall_connector_contactor_closed", "off", "on"
        ),
        EntityAndExpectedValues(
            "binary_sensor.tesla_wall_connector_vehicle_connected", "on", "off"
        ),
    ]

    mock_vitals_first_update = get_vitals_mock()

    mock_vitals_second_update = get_vitals_mock()
    mock_vitals_second_update.contactor_closed = True
    mock_vitals_second_update.vehicle_connected = False

    lifetime_mock = get_lifetime_mock()

    await _test_sensors(
        menuai,
        entities_and_expected_values=entity_and_expected_values,
        vitals_first_update=mock_vitals_first_update,
        vitals_second_update=mock_vitals_second_update,
        lifetime_first_update=lifetime_mock,
        lifetime_second_update=lifetime_mock,
    )
