"""Test Homee alarm control panels."""

from unittest.mock import MagicMock, patch

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.alarm_control_panel import (
    DOMAIN as ALARM_CONTROL_PANEL_DOMAIN,
    SERVICE_ALARM_ARM_AWAY,
    SERVICE_ALARM_ARM_HOME,
    SERVICE_ALARM_ARM_NIGHT,
    SERVICE_ALARM_ARM_VACATION,
    SERVICE_ALARM_DISARM,
)
from menuai.components.homee.const import DOMAIN
from menuai.const import ATTR_ENTITY_ID, Platform
from menuai.core import menuai
from menuai.exceptions import ServiceValidationError
from menuai.helpers import entity_registry as er

from . import build_mock_node, setup_integration

from tests.common import MockConfigEntry, snapshot_platform


async def setup_alarm_control_panel(
    menuai: menuai, mock_homee: MagicMock, mock_config_entry: MockConfigEntry
) -> None:
    """Setups the integration for select tests."""
    mock_homee.nodes = [build_mock_node("homee.json")]
    mock_homee.get_node_by_id.return_value = mock_homee.nodes[0]
    await setup_integration(menuai, mock_config_entry)


@pytest.mark.parametrize(
    ("service", "state"),
    [
        (SERVICE_ALARM_ARM_HOME, 0),
        (SERVICE_ALARM_ARM_NIGHT, 1),
        (SERVICE_ALARM_ARM_AWAY, 2),
        (SERVICE_ALARM_ARM_VACATION, 3),
    ],
)
async def test_alarm_control_panel_services(
    menuai: menuai,
    mock_homee: MagicMock,
    mock_config_entry: MockConfigEntry,
    service: str,
    state: int,
) -> None:
    """Test alarm control panel services."""
    await setup_alarm_control_panel(menuai, mock_homee, mock_config_entry)

    await menuai.services.async_call(
        ALARM_CONTROL_PANEL_DOMAIN,
        service,
        {ATTR_ENTITY_ID: "alarm_control_panel.testhomee_status"},
        blocking=True,
    )
    mock_homee.set_value.assert_called_once_with(-1, 1, state)


async def test_alarm_control_panel_service_disarm_error(
    menuai: menuai,
    mock_homee: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test that disarm service calls no action."""
    await setup_alarm_control_panel(menuai, mock_homee, mock_config_entry)

    with pytest.raises(ServiceValidationError) as exc_info:
        await menuai.services.async_call(
            ALARM_CONTROL_PANEL_DOMAIN,
            SERVICE_ALARM_DISARM,
            {ATTR_ENTITY_ID: "alarm_control_panel.testhomee_status"},
            blocking=True,
        )
    assert exc_info.value.translation_domain == DOMAIN
    assert exc_info.value.translation_key == "disarm_not_supported"


async def test_alarm_control_panel_snapshot(
    menuai: menuai,
    mock_homee: MagicMock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the alarm-control_panel snapshots."""
    with patch(
        "menuai.components.homee.PLATFORMS", [Platform.ALARM_CONTROL_PANEL]
    ):
        await setup_alarm_control_panel(menuai, mock_homee, mock_config_entry)

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)
