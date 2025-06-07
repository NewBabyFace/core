"""The water heater tests for the Airzone platform."""

from unittest.mock import patch

from aioairzone.const import (
    API_ACS_ON,
    API_ACS_POWER_MODE,
    API_ACS_SET_POINT,
    API_DATA,
    API_SYSTEM_ID,
)
from aioairzone.exceptions import AirzoneError
import pytest

from menuai.components.water_heater import (
    ATTR_CURRENT_TEMPERATURE,
    ATTR_MAX_TEMP,
    ATTR_MIN_TEMP,
    ATTR_OPERATION_MODE,
    DOMAIN as WATER_HEATER_DOMAIN,
    SERVICE_SET_OPERATION_MODE,
    SERVICE_SET_TEMPERATURE,
    STATE_ECO,
    STATE_PERFORMANCE,
)
from menuai.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
)
from menuai.core import menuai
from menuai.exceptions import menuaiError

from .util import async_init_integration


async def test_airzone_create_water_heater(menuai: menuai) -> None:
    """Test creation of water heater."""

    await async_init_integration(menuai)

    state = menuai.states.get("water_heater.airzone_dhw")
    assert state.state == STATE_ECO
    assert state.attributes[ATTR_CURRENT_TEMPERATURE] == 43
    assert state.attributes[ATTR_MAX_TEMP] == 75
    assert state.attributes[ATTR_MIN_TEMP] == 30
    assert state.attributes[ATTR_TEMPERATURE] == 45


async def test_airzone_water_heater_turn_on_off(menuai: menuai) -> None:
    """Test turning on/off."""

    await async_init_integration(menuai)

    HVAC_MOCK = {
        API_DATA: {
            API_SYSTEM_ID: 0,
            API_ACS_ON: 0,
        }
    }
    with patch(
        "menuai.components.airzone.AirzoneLocalApi.put_hvac",
        return_value=HVAC_MOCK,
    ):
        await menuai.services.async_call(
            WATER_HEATER_DOMAIN,
            SERVICE_TURN_OFF,
            {
                ATTR_ENTITY_ID: "water_heater.airzone_dhw",
            },
            blocking=True,
        )

    state = menuai.states.get("water_heater.airzone_dhw")
    assert state.state == STATE_OFF

    HVAC_MOCK = {
        API_DATA: {
            API_SYSTEM_ID: 0,
            API_ACS_ON: 1,
        }
    }
    with patch(
        "menuai.components.airzone.AirzoneLocalApi.put_hvac",
        return_value=HVAC_MOCK,
    ):
        await menuai.services.async_call(
            WATER_HEATER_DOMAIN,
            SERVICE_TURN_ON,
            {
                ATTR_ENTITY_ID: "water_heater.airzone_dhw",
            },
            blocking=True,
        )

    state = menuai.states.get("water_heater.airzone_dhw")
    assert state.state == STATE_ECO


async def test_airzone_water_heater_set_operation(menuai: menuai) -> None:
    """Test setting the Operation mode."""

    await async_init_integration(menuai)

    HVAC_MOCK_1 = {
        API_DATA: {
            API_SYSTEM_ID: 0,
            API_ACS_ON: 0,
        }
    }
    with patch(
        "menuai.components.airzone.AirzoneLocalApi.put_hvac",
        return_value=HVAC_MOCK_1,
    ):
        await menuai.services.async_call(
            WATER_HEATER_DOMAIN,
            SERVICE_SET_OPERATION_MODE,
            {
                ATTR_ENTITY_ID: "water_heater.airzone_dhw",
                ATTR_OPERATION_MODE: STATE_OFF,
            },
            blocking=True,
        )

    state = menuai.states.get("water_heater.airzone_dhw")
    assert state.state == STATE_OFF

    HVAC_MOCK_2 = {
        API_DATA: {
            API_SYSTEM_ID: 0,
            API_ACS_ON: 1,
            API_ACS_POWER_MODE: 1,
        }
    }
    with patch(
        "menuai.components.airzone.AirzoneLocalApi.put_hvac",
        return_value=HVAC_MOCK_2,
    ):
        await menuai.services.async_call(
            WATER_HEATER_DOMAIN,
            SERVICE_SET_OPERATION_MODE,
            {
                ATTR_ENTITY_ID: "water_heater.airzone_dhw",
                ATTR_OPERATION_MODE: STATE_PERFORMANCE,
            },
            blocking=True,
        )

    state = menuai.states.get("water_heater.airzone_dhw")
    assert state.state == STATE_PERFORMANCE

    HVAC_MOCK_3 = {
        API_DATA: {
            API_SYSTEM_ID: 0,
            API_ACS_ON: 1,
            API_ACS_POWER_MODE: 0,
        }
    }
    with patch(
        "menuai.components.airzone.AirzoneLocalApi.put_hvac",
        return_value=HVAC_MOCK_3,
    ):
        await menuai.services.async_call(
            WATER_HEATER_DOMAIN,
            SERVICE_SET_OPERATION_MODE,
            {
                ATTR_ENTITY_ID: "water_heater.airzone_dhw",
                ATTR_OPERATION_MODE: STATE_ECO,
            },
            blocking=True,
        )

    state = menuai.states.get("water_heater.airzone_dhw")
    assert state.state == STATE_ECO


async def test_airzone_water_heater_set_temp(menuai: menuai) -> None:
    """Test setting the target temperature."""

    HVAC_MOCK = {
        API_DATA: {
            API_SYSTEM_ID: 0,
            API_ACS_SET_POINT: 35,
        }
    }

    await async_init_integration(menuai)

    with patch(
        "menuai.components.airzone.AirzoneLocalApi.put_hvac",
        return_value=HVAC_MOCK,
    ):
        await menuai.services.async_call(
            WATER_HEATER_DOMAIN,
            SERVICE_SET_TEMPERATURE,
            {
                ATTR_ENTITY_ID: "water_heater.airzone_dhw",
                ATTR_TEMPERATURE: 35,
            },
            blocking=True,
        )

    state = menuai.states.get("water_heater.airzone_dhw")
    assert state.attributes[ATTR_TEMPERATURE] == 35


async def test_airzone_water_heater_set_temp_error(menuai: menuai) -> None:
    """Test error when setting the target temperature."""

    await async_init_integration(menuai)

    with (
        patch(
            "menuai.components.airzone.AirzoneLocalApi.put_hvac",
            side_effect=AirzoneError,
        ),
        pytest.raises(menuaiError),
    ):
        await menuai.services.async_call(
            WATER_HEATER_DOMAIN,
            SERVICE_SET_TEMPERATURE,
            {
                ATTR_ENTITY_ID: "water_heater.airzone_dhw",
                ATTR_TEMPERATURE: 80,
            },
            blocking=True,
        )

    state = menuai.states.get("water_heater.airzone_dhw")
    assert state.attributes[ATTR_TEMPERATURE] == 45
