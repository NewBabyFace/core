"""Test Snoo Switches."""

import copy
from unittest.mock import AsyncMock

import pytest
from python_snoo.containers import SnooDevice
from python_snoo.exceptions import SnooCommandException

from menuai.components.switch import (
    SERVICE_TOGGLE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from menuai.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE
from menuai.core import menuai
from menuai.exceptions import menuaiError

from . import async_init_integration, find_update_callback
from .const import MOCK_SNOO_DATA


async def test_switch(menuai: menuai, bypass_api: AsyncMock) -> None:
    """Test switch and check test values are correctly set."""
    await async_init_integration(menuai)
    assert len(menuai.states.async_all("switch")) == 2
    assert menuai.states.get("switch.test_snoo_level_lock").state == STATE_UNAVAILABLE
    assert (
        menuai.states.get("switch.test_snoo_sleepytime_sounds").state == STATE_UNAVAILABLE
    )
    find_update_callback(bypass_api, "random_num")(MOCK_SNOO_DATA)
    await menuai.async_block_till_done()
    assert len(menuai.states.async_all("switch")) == 2
    assert menuai.states.get("switch.test_snoo_sleepytime_sounds").state == STATE_OFF
    assert menuai.states.get("switch.test_snoo_level_lock").state == STATE_OFF


async def test_update_success(menuai: menuai, bypass_api: AsyncMock) -> None:
    """Test changing values for switch entities."""
    await async_init_integration(menuai)

    find_update_callback(bypass_api, "random_num")(MOCK_SNOO_DATA)
    assert menuai.states.get("switch.test_snoo_sleepytime_sounds").state == STATE_OFF

    async def set_sticky_white_noise(device: SnooDevice, state: bool):
        new_data = copy.deepcopy(MOCK_SNOO_DATA)
        new_data.state_machine.sticky_white_noise = "off" if not state else "on"
        find_update_callback(bypass_api, device.serialNumber)(new_data)

    bypass_api.set_sticky_white_noise.side_effect = set_sticky_white_noise
    await menuai.services.async_call(
        "switch",
        SERVICE_TOGGLE,
        blocking=True,
        target={"entity_id": "switch.test_snoo_sleepytime_sounds"},
    )

    assert bypass_api.set_sticky_white_noise.assert_called_once
    assert menuai.states.get("switch.test_snoo_sleepytime_sounds").state == STATE_ON


@pytest.mark.parametrize(
    ("command", "error_str"),
    [
        (SERVICE_TURN_ON, "Turning Sleepytime sounds on failed"),
        (SERVICE_TURN_OFF, "Turning Sleepytime sounds off failed"),
    ],
)
async def test_update_failed(
    menuai: menuai, bypass_api: AsyncMock, command: str, error_str: str
) -> None:
    """Test failing to change values for switch entities."""
    await async_init_integration(menuai)

    find_update_callback(bypass_api, "random_num")(MOCK_SNOO_DATA)
    assert menuai.states.get("switch.test_snoo_sleepytime_sounds").state == STATE_OFF

    bypass_api.set_sticky_white_noise.side_effect = SnooCommandException
    with pytest.raises(menuaiError, match=error_str):
        await menuai.services.async_call(
            "switch",
            command,
            blocking=True,
            target={"entity_id": "switch.test_snoo_sleepytime_sounds"},
        )

    assert bypass_api.set_level.assert_called_once
    assert menuai.states.get("switch.test_snoo_sleepytime_sounds").state == STATE_OFF
