"""Tests for Bosch Alarm component."""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.alarm_control_panel import (
    DOMAIN as ALARM_CONTROL_PANEL_DOMAIN,
    AlarmControlPanelState,
)
from menuai.const import (
    ATTR_ENTITY_ID,
    SERVICE_ALARM_ARM_AWAY,
    SERVICE_ALARM_ARM_HOME,
    SERVICE_ALARM_DISARM,
    STATE_UNAVAILABLE,
    Platform,
)
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import call_observable, setup_integration

from tests.common import MockConfigEntry, snapshot_platform


@pytest.fixture(autouse=True)
async def platforms() -> AsyncGenerator[None]:
    """Return the platforms to be loaded for this test."""
    with patch(
        "menuai.components.bosch_alarm.PLATFORMS", [Platform.ALARM_CONTROL_PANEL]
    ):
        yield


async def test_update_alarm_device(
    menuai: menuai,
    mock_panel: AsyncMock,
    area: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test that alarm panel state changes after arming the panel."""
    await setup_integration(menuai, mock_config_entry)
    entity_id = "alarm_control_panel.area1"
    assert menuai.states.get(entity_id).state == AlarmControlPanelState.DISARMED

    area.is_arming.return_value = True
    area.is_disarmed.return_value = False

    await menuai.services.async_call(
        ALARM_CONTROL_PANEL_DOMAIN,
        SERVICE_ALARM_ARM_AWAY,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    await call_observable(menuai, area.status_observer)

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.ARMING

    area.is_arming.return_value = False
    area.is_all_armed.return_value = True

    await call_observable(menuai, area.status_observer)

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.ARMED_AWAY

    await menuai.services.async_call(
        ALARM_CONTROL_PANEL_DOMAIN,
        SERVICE_ALARM_DISARM,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )

    area.is_all_armed.return_value = False
    area.is_disarmed.return_value = True

    await call_observable(menuai, area.status_observer)

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.DISARMED
    await menuai.services.async_call(
        ALARM_CONTROL_PANEL_DOMAIN,
        SERVICE_ALARM_ARM_HOME,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )

    area.is_disarmed.return_value = False
    area.is_arming.return_value = True

    await call_observable(menuai, area.status_observer)

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.ARMING

    area.is_arming.return_value = False
    area.is_part_armed.return_value = True

    await call_observable(menuai, area.status_observer)

    assert menuai.states.get(entity_id).state == AlarmControlPanelState.ARMED_HOME
    await menuai.services.async_call(
        ALARM_CONTROL_PANEL_DOMAIN,
        SERVICE_ALARM_DISARM,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    area.is_part_armed.return_value = False
    area.is_disarmed.return_value = True

    await call_observable(menuai, area.status_observer)
    assert menuai.states.get(entity_id).state == AlarmControlPanelState.DISARMED


async def test_alarm_control_panel(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    mock_panel: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the alarm_control_panel state."""
    await setup_integration(menuai, mock_config_entry)

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


async def test_alarm_control_panel_availability(
    menuai: menuai,
    mock_panel: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the alarm_control_panel availability."""
    await setup_integration(menuai, mock_config_entry)

    assert (
        menuai.states.get("alarm_control_panel.area1").state
        == AlarmControlPanelState.DISARMED
    )

    mock_panel.connection_status.return_value = False

    await call_observable(menuai, mock_panel.connection_status_observer)

    assert menuai.states.get("alarm_control_panel.area1").state == STATE_UNAVAILABLE
