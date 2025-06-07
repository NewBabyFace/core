"""Tests for Vanderbilt SPC component."""

from unittest.mock import AsyncMock

from pyspcwebgw.const import AreaMode

from menuai.components.alarm_control_panel import AlarmControlPanelState
from menuai.core import menuai
from menuai.setup import async_setup_component


async def test_update_alarm_device(menuai: menuai, mock_client: AsyncMock) -> None:
    """Test that alarm panel state changes on incoming websocket data."""

    config = {"spc": {"api_url": "http://localhost/", "ws_url": "ws://localhost/"}}
    assert await async_setup_component(menuai, "spc", config) is True

    await menuai.async_block_till_done()

    entity_id = "alarm_control_panel.house"

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.ARMED_AWAY
    assert menuai.states.get(entity_id).attributes["changed_by"] == "Sven"

    mock_area = mock_client.return_value.areas["1"]

    mock_area.mode = AreaMode.UNSET
    mock_area.last_changed_by = "Anna"

    await mock_client.call_args_list[0][1]["async_callback"](mock_area)
    await menuai.async_block_till_done()

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.DISARMED
    assert menuai.states.get(entity_id).attributes["changed_by"] == "Anna"
