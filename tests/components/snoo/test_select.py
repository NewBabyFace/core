"""Test Snoo Selects."""

import copy
from unittest.mock import AsyncMock

import pytest
from python_snoo.containers import SnooDevice, SnooLevels, SnooStates

from menuai.components.select import SERVICE_SELECT_OPTION
from menuai.components.snoo.select import SnooCommandException
from menuai.const import STATE_UNAVAILABLE
from menuai.core import menuai
from menuai.exceptions import menuaiError

from . import async_init_integration, find_update_callback
from .const import MOCK_SNOO_DATA


async def test_select(menuai: menuai, bypass_api: AsyncMock) -> None:
    """Test select and check test values are correctly set."""
    await async_init_integration(menuai)
    assert len(menuai.states.async_all("select")) == 1
    assert menuai.states.get("select.test_snoo_intensity").state == STATE_UNAVAILABLE
    find_update_callback(bypass_api, "random_num")(MOCK_SNOO_DATA)
    await menuai.async_block_till_done()
    assert len(menuai.states.async_all("select")) == 1
    assert menuai.states.get("select.test_snoo_intensity").state == "stop"


async def test_update_success(menuai: menuai, bypass_api: AsyncMock) -> None:
    """Test changing values for select entities."""
    await async_init_integration(menuai)

    find_update_callback(bypass_api, "random_num")(MOCK_SNOO_DATA)
    assert menuai.states.get("select.test_snoo_intensity").state == "stop"

    async def update_level(device: SnooDevice, level: SnooStates, _hold: bool = False):
        new_data = copy.deepcopy(MOCK_SNOO_DATA)
        new_data.state_machine.level = SnooLevels(level.value)
        find_update_callback(bypass_api, device.serialNumber)(new_data)

    bypass_api.set_level.side_effect = update_level
    await menuai.services.async_call(
        "select",
        SERVICE_SELECT_OPTION,
        service_data={"option": "level1"},
        blocking=True,
        target={"entity_id": "select.test_snoo_intensity"},
    )

    assert bypass_api.set_level.assert_called_once
    assert menuai.states.get("select.test_snoo_intensity").state == "level1"


async def test_update_failed(menuai: menuai, bypass_api: AsyncMock) -> None:
    """Test failing to change values for select entities."""
    await async_init_integration(menuai)

    find_update_callback(bypass_api, "random_num")(MOCK_SNOO_DATA)
    assert menuai.states.get("select.test_snoo_intensity").state == "stop"

    bypass_api.set_level.side_effect = SnooCommandException
    with pytest.raises(
        menuaiError, match="Error while updating Intensity to level1"
    ):
        await menuai.services.async_call(
            "select",
            SERVICE_SELECT_OPTION,
            service_data={"option": "level1"},
            blocking=True,
            target={"entity_id": "select.test_snoo_intensity"},
        )

    assert bypass_api.set_level.assert_called_once
    assert menuai.states.get("select.test_snoo_intensity").state == "stop"
