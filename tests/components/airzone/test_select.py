"""The select tests for the Airzone platform."""

from unittest.mock import patch

from aioairzone.common import OperationMode
from aioairzone.const import (
    API_COLD_ANGLE,
    API_DATA,
    API_HEAT_ANGLE,
    API_MODE,
    API_SLEEP,
    API_SYSTEM_ID,
    API_ZONE_ID,
)
import pytest

from menuai.components.select import ATTR_OPTIONS, DOMAIN as SELECT_DOMAIN
from menuai.const import ATTR_ENTITY_ID, ATTR_OPTION, SERVICE_SELECT_OPTION
from menuai.core import menuai
from menuai.exceptions import ServiceValidationError

from .util import async_init_integration


async def test_airzone_create_selects(menuai: menuai) -> None:
    """Test creation of selects."""

    await async_init_integration(menuai)

    state = menuai.states.get("select.despacho_cold_angle")
    assert state.state == "90deg"

    state = menuai.states.get("select.despacho_heat_angle")
    assert state.state == "90deg"

    state = menuai.states.get("select.despacho_mode")
    assert state is None

    state = menuai.states.get("select.despacho_sleep")
    assert state.state == "off"

    state = menuai.states.get("select.dorm_1_cold_angle")
    assert state.state == "90deg"

    state = menuai.states.get("select.dorm_1_heat_angle")
    assert state.state == "90deg"

    state = menuai.states.get("select.dorm_1_mode")
    assert state is None

    state = menuai.states.get("select.dorm_1_sleep")
    assert state.state == "off"

    state = menuai.states.get("select.dorm_2_cold_angle")
    assert state.state == "90deg"

    state = menuai.states.get("select.dorm_2_heat_angle")
    assert state.state == "90deg"

    state = menuai.states.get("select.dorm_2_mode")
    assert state is None

    state = menuai.states.get("select.dorm_2_sleep")
    assert state.state == "off"

    state = menuai.states.get("select.dorm_ppal_cold_angle")
    assert state.state == "45deg"

    state = menuai.states.get("select.dorm_ppal_heat_angle")
    assert state.state == "50deg"

    state = menuai.states.get("select.dorm_ppal_mode")
    assert state is None

    state = menuai.states.get("select.dorm_ppal_sleep")
    assert state.state == "30m"

    state = menuai.states.get("select.salon_cold_angle")
    assert state.state == "90deg"

    state = menuai.states.get("select.salon_heat_angle")
    assert state.state == "90deg"

    state = menuai.states.get("select.salon_mode")
    assert state.state == "heat"
    assert state.attributes.get(ATTR_OPTIONS) == [
        "cool",
        "dry",
        "fan",
        "heat",
        "stop",
    ]

    state = menuai.states.get("select.salon_sleep")
    assert state.state == "off"


async def test_airzone_select_sleep(menuai: menuai) -> None:
    """Test select sleep."""

    await async_init_integration(menuai)

    put_hvac_sleep = {
        API_DATA: [
            {
                API_SYSTEM_ID: 1,
                API_ZONE_ID: 3,
                API_SLEEP: 30,
            }
        ]
    }

    with pytest.raises(ServiceValidationError):
        await menuai.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {
                ATTR_ENTITY_ID: "select.dorm_1_sleep",
                ATTR_OPTION: "Invalid",
            },
            blocking=True,
        )

    with patch(
        "menuai.components.airzone.AirzoneLocalApi.put_hvac",
        return_value=put_hvac_sleep,
    ):
        await menuai.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {
                ATTR_ENTITY_ID: "select.dorm_1_sleep",
                ATTR_OPTION: "30m",
            },
            blocking=True,
        )

    state = menuai.states.get("select.dorm_1_sleep")
    assert state.state == "30m"


async def test_airzone_select_mode(menuai: menuai) -> None:
    """Test select HVAC mode."""

    await async_init_integration(menuai)

    put_hvac_mode = {
        API_DATA: [
            {
                API_SYSTEM_ID: 1,
                API_ZONE_ID: 1,
                API_MODE: OperationMode.COOLING,
            }
        ]
    }

    with pytest.raises(ServiceValidationError):
        await menuai.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {
                ATTR_ENTITY_ID: "select.salon_mode",
                ATTR_OPTION: "Invalid",
            },
            blocking=True,
        )

    with patch(
        "menuai.components.airzone.AirzoneLocalApi.put_hvac",
        return_value=put_hvac_mode,
    ):
        await menuai.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {
                ATTR_ENTITY_ID: "select.salon_mode",
                ATTR_OPTION: "cool",
            },
            blocking=True,
        )

    state = menuai.states.get("select.salon_mode")
    assert state.state == "cool"


async def test_airzone_select_grille_angle(menuai: menuai) -> None:
    """Test select sleep."""

    await async_init_integration(menuai)

    # Cold Angle

    put_hvac_cold_angle = {
        API_DATA: [
            {
                API_SYSTEM_ID: 1,
                API_ZONE_ID: 3,
                API_COLD_ANGLE: 1,
            }
        ]
    }

    with patch(
        "menuai.components.airzone.AirzoneLocalApi.put_hvac",
        return_value=put_hvac_cold_angle,
    ):
        await menuai.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {
                ATTR_ENTITY_ID: "select.dorm_1_cold_angle",
                ATTR_OPTION: "50deg",
            },
            blocking=True,
        )

    state = menuai.states.get("select.dorm_1_cold_angle")
    assert state.state == "50deg"

    # Heat Angle

    put_hvac_heat_angle = {
        API_DATA: [
            {
                API_SYSTEM_ID: 1,
                API_ZONE_ID: 3,
                API_HEAT_ANGLE: 2,
            }
        ]
    }
    with patch(
        "menuai.components.airzone.AirzoneLocalApi.put_hvac",
        return_value=put_hvac_heat_angle,
    ):
        await menuai.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {
                ATTR_ENTITY_ID: "select.dorm_1_heat_angle",
                ATTR_OPTION: "45deg",
            },
            blocking=True,
        )

    state = menuai.states.get("select.dorm_1_heat_angle")
    assert state.state == "45deg"
