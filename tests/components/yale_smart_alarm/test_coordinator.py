"""The test for the sensibo coordinator."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import Mock, patch

import pytest
from yalesmartalarmclient import (
    YALE_STATE_ARM_FULL,
    AuthenticationError,
    UnknownError,
    YaleSmartAlarmData,
)

from menuai.components.alarm_control_panel import AlarmControlPanelState
from menuai.components.yale_smart_alarm.const import DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.const import STATE_UNAVAILABLE
from menuai.core import menuai
from menuai.util import dt as dt_util

from .conftest import ENTRY_CONFIG, OPTIONS_CONFIG

from tests.common import MockConfigEntry, async_fire_time_changed


@pytest.mark.parametrize(
    "p_error",
    [
        AuthenticationError(),
        UnknownError(),
        ConnectionError("Could not connect"),
        TimeoutError(),
    ],
)
async def test_coordinator_setup_errors(
    menuai: menuai,
    get_data: YaleSmartAlarmData,
    p_error: Exception,
) -> None:
    """Test the Yale Smart Living coordinator with errors."""

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        source=SOURCE_USER,
        data=ENTRY_CONFIG,
        options=OPTIONS_CONFIG,
        entry_id="1",
        unique_id="username",
        version=2,
        minor_version=2,
    )

    config_entry.add_to_menuai(menuai)

    with patch(
        "menuai.components.yale_smart_alarm.coordinator.YaleSmartAlarmClient",
        autospec=True,
    ) as mock_client_class:
        mock_client_class.side_effect = p_error
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    state = menuai.states.get("alarm_control_panel.test_username")
    assert not state


async def test_coordinator_setup_and_update_errors(
    menuai: menuai,
    load_config_entry: tuple[MockConfigEntry, Mock],
    get_data: YaleSmartAlarmData,
) -> None:
    """Test the Yale Smart Living coordinator with errors."""

    client = load_config_entry[1]

    state = menuai.states.get("alarm_control_panel.test_username")
    assert state.state == AlarmControlPanelState.ARMED_AWAY
    client.reset_mock()

    client.get_information.side_effect = ConnectionError("Could not connect")
    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(minutes=1))
    await menuai.async_block_till_done(wait_background_tasks=True)
    client.get_information.assert_called_once()
    state = menuai.states.get("alarm_control_panel.test_username")
    assert state.state == STATE_UNAVAILABLE
    client.reset_mock()

    client.get_information.side_effect = ConnectionError("Could not connect")
    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(minutes=2))
    await menuai.async_block_till_done(wait_background_tasks=True)
    client.get_information.assert_called_once()
    state = menuai.states.get("alarm_control_panel.test_username")
    assert state.state == STATE_UNAVAILABLE
    client.reset_mock()

    client.get_information.side_effect = TimeoutError("Could not connect")
    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(minutes=3))
    await menuai.async_block_till_done(wait_background_tasks=True)
    client.get_information.assert_called_once()
    state = menuai.states.get("alarm_control_panel.test_username")
    assert state.state == STATE_UNAVAILABLE
    client.reset_mock()

    client.get_information.side_effect = UnknownError("info")
    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(minutes=4))
    await menuai.async_block_till_done(wait_background_tasks=True)
    client.get_information.assert_called_once()
    state = menuai.states.get("alarm_control_panel.test_username")
    assert state.state == STATE_UNAVAILABLE
    client.reset_mock()

    client.get_information.side_effect = None
    client.get_information.return_value = get_data
    client.get_armed_status.return_value = YALE_STATE_ARM_FULL
    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(minutes=5))
    await menuai.async_block_till_done(wait_background_tasks=True)
    client.get_information.assert_called_once()
    state = menuai.states.get("alarm_control_panel.test_username")
    assert state.state == AlarmControlPanelState.ARMED_AWAY
    client.reset_mock()

    client.get_information.side_effect = AuthenticationError("Can not authenticate")
    async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(minutes=6))
    await menuai.async_block_till_done(wait_background_tasks=True)
    client.get_information.assert_called_once()
    state = menuai.states.get("alarm_control_panel.test_username")
    assert state.state == STATE_UNAVAILABLE
