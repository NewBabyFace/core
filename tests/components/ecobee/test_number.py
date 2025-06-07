"""The test for the ecobee thermostat number module."""

from unittest.mock import patch

from menuai.components.number import (
    ATTR_VALUE,
    DOMAIN as NUMBER_DOMAIN,
    SERVICE_SET_VALUE,
)
from menuai.const import ATTR_ENTITY_ID, UnitOfTime
from menuai.core import menuai

from .common import setup_platform

VENTILATOR_MIN_HOME_ID = "number.ecobee_ventilator_minimum_time_home"
VENTILATOR_MIN_AWAY_ID = "number.ecobee_ventilator_minimum_time_away"
THERMOSTAT_ID = 0


async def test_ventilator_min_on_home_attributes(menuai: menuai) -> None:
    """Test the ventilator number on home attributes are correct."""
    await setup_platform(menuai, NUMBER_DOMAIN)

    state = menuai.states.get(VENTILATOR_MIN_HOME_ID)
    assert state.state == "20"
    assert state.attributes.get("min") == 0
    assert state.attributes.get("max") == 60
    assert state.attributes.get("step") == 5
    assert (
        state.attributes.get("friendly_name") == "ecobee Ventilator minimum time home"
    )
    assert state.attributes.get("unit_of_measurement") == UnitOfTime.MINUTES


async def test_ventilator_min_on_away_attributes(menuai: menuai) -> None:
    """Test the ventilator number on away attributes are correct."""
    await setup_platform(menuai, NUMBER_DOMAIN)

    state = menuai.states.get(VENTILATOR_MIN_AWAY_ID)
    assert state.state == "10"
    assert state.attributes.get("min") == 0
    assert state.attributes.get("max") == 60
    assert state.attributes.get("step") == 5
    assert (
        state.attributes.get("friendly_name") == "ecobee Ventilator minimum time away"
    )
    assert state.attributes.get("unit_of_measurement") == UnitOfTime.MINUTES


async def test_set_min_time_home(menuai: menuai) -> None:
    """Test the number can set min time home."""
    target_value = 40
    with patch(
        "menuai.components.ecobee.Ecobee.set_ventilator_min_on_time_home"
    ) as mock_set_min_home_time:
        await setup_platform(menuai, NUMBER_DOMAIN)

        await menuai.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {ATTR_ENTITY_ID: VENTILATOR_MIN_HOME_ID, ATTR_VALUE: target_value},
            blocking=True,
        )
        await menuai.async_block_till_done()
        mock_set_min_home_time.assert_called_once_with(THERMOSTAT_ID, target_value)


async def test_set_min_time_away(menuai: menuai) -> None:
    """Test the number can set min time away."""
    target_value = 0
    with patch(
        "menuai.components.ecobee.Ecobee.set_ventilator_min_on_time_away"
    ) as mock_set_min_away_time:
        await setup_platform(menuai, NUMBER_DOMAIN)

        await menuai.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {ATTR_ENTITY_ID: VENTILATOR_MIN_AWAY_ID, ATTR_VALUE: target_value},
            blocking=True,
        )
        await menuai.async_block_till_done()
        mock_set_min_away_time.assert_called_once_with(THERMOSTAT_ID, target_value)


COMPRESSOR_MIN_TEMP_ID = "number.ecobee2_compressor_minimum_temperature"


async def test_compressor_protection_min_temp_attributes(menuai: menuai) -> None:
    """Test the compressor min temp value is correct.

    Ecobee runs in Fahrenheit; the test rig runs in Celsius. Conversions are necessary.
    """
    await setup_platform(menuai, NUMBER_DOMAIN)

    state = menuai.states.get(COMPRESSOR_MIN_TEMP_ID)
    assert state.state == "-12.2"
    assert (
        state.attributes.get("friendly_name")
        == "ecobee2 Compressor minimum temperature"
    )


async def test_set_compressor_protection_min_temp(menuai: menuai) -> None:
    """Test the number can set minimum compressor operating temp.

    Ecobee runs in Fahrenheit; the test rig runs in Celsius. Conversions are necessary
    """
    target_value = 0
    with patch(
        "menuai.components.ecobee.Ecobee.set_aux_cutover_threshold"
    ) as mock_set_compressor_min_temp:
        await setup_platform(menuai, NUMBER_DOMAIN)

        await menuai.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {ATTR_ENTITY_ID: COMPRESSOR_MIN_TEMP_ID, ATTR_VALUE: target_value},
            blocking=True,
        )
        await menuai.async_block_till_done()
        mock_set_compressor_min_temp.assert_called_once_with(1, 32)
