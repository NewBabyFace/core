"""The switch tests for the Airzone platform."""

from unittest.mock import patch

from aioairzone.const import API_DATA, API_ON, API_SYSTEM_ID, API_ZONE_ID

from menuai.components.switch import DOMAIN as SWITCH_DOMAIN
from menuai.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from menuai.core import menuai

from .util import async_init_integration


async def test_airzone_create_switches(menuai: menuai) -> None:
    """Test creation of switches."""

    await async_init_integration(menuai)

    state = menuai.states.get("switch.despacho")
    assert state.state == STATE_OFF

    state = menuai.states.get("switch.dorm_1")
    assert state.state == STATE_ON

    state = menuai.states.get("switch.dorm_2")
    assert state.state == STATE_OFF

    state = menuai.states.get("switch.dorm_ppal")
    assert state.state == STATE_ON

    state = menuai.states.get("switch.salon")
    assert state.state == STATE_OFF


async def test_airzone_switch_off(menuai: menuai) -> None:
    """Test switch off."""

    await async_init_integration(menuai)

    put_hvac_off = {
        API_DATA: [
            {
                API_SYSTEM_ID: 1,
                API_ZONE_ID: 3,
                API_ON: False,
            }
        ]
    }

    with patch(
        "menuai.components.airzone.AirzoneLocalApi.put_hvac",
        return_value=put_hvac_off,
    ):
        await menuai.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {
                ATTR_ENTITY_ID: "switch.dorm_1",
            },
            blocking=True,
        )

    state = menuai.states.get("switch.dorm_1")
    assert state.state == STATE_OFF


async def test_airzone_switch_on(menuai: menuai) -> None:
    """Test switch on."""

    await async_init_integration(menuai)

    put_hvac_on = {
        API_DATA: [
            {
                API_SYSTEM_ID: 1,
                API_ZONE_ID: 5,
                API_ON: True,
            }
        ]
    }

    with patch(
        "menuai.components.airzone.AirzoneLocalApi.put_hvac",
        return_value=put_hvac_on,
    ):
        await menuai.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {
                ATTR_ENTITY_ID: "switch.dorm_2",
            },
            blocking=True,
        )

    state = menuai.states.get("switch.dorm_2")
    assert state.state == STATE_ON
