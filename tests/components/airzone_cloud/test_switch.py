"""The switch tests for the Airzone Cloud platform."""

from unittest.mock import patch

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

    state = menuai.states.get("switch.dormitorio")
    assert state.state == STATE_OFF

    state = menuai.states.get("switch.salon")
    assert state.state == STATE_ON


async def test_airzone_switch_off(menuai: menuai) -> None:
    """Test switch off."""

    await async_init_integration(menuai)

    with patch(
        "menuai.components.airzone_cloud.AirzoneCloudApi.api_patch_device",
        return_value=None,
    ):
        await menuai.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {
                ATTR_ENTITY_ID: "switch.salon",
            },
            blocking=True,
        )

    state = menuai.states.get("switch.salon")
    assert state.state == STATE_OFF


async def test_airzone_switch_on(menuai: menuai) -> None:
    """Test switch on."""

    await async_init_integration(menuai)

    with patch(
        "menuai.components.airzone_cloud.AirzoneCloudApi.api_patch_device",
        return_value=None,
    ):
        await menuai.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {
                ATTR_ENTITY_ID: "switch.dormitorio",
            },
            blocking=True,
        )

    state = menuai.states.get("switch.dormitorio")
    assert state.state == STATE_ON
