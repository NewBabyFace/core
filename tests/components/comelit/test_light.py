"""Tests for Comelit SimpleHome light platform."""

from unittest.mock import AsyncMock, patch

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.light import (
    DOMAIN as LIGHT_DOMAIN,
    SERVICE_TOGGLE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from menuai.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import setup_integration

from tests.common import MockConfigEntry, snapshot_platform

ENTITY_ID = "light.light0"


async def test_all_entities(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    mock_serial_bridge: AsyncMock,
    mock_serial_bridge_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test all entities."""
    with patch("menuai.components.comelit.BRIDGE_PLATFORMS", [Platform.LIGHT]):
        await setup_integration(menuai, mock_serial_bridge_config_entry)

    await snapshot_platform(
        menuai,
        entity_registry,
        snapshot,
        mock_serial_bridge_config_entry.entry_id,
    )


@pytest.mark.parametrize(
    ("service", "status"),
    [
        (SERVICE_TURN_OFF, STATE_OFF),
        (SERVICE_TURN_ON, STATE_ON),
        (SERVICE_TOGGLE, STATE_ON),
    ],
)
async def test_light_set_state(
    menuai: menuai,
    mock_serial_bridge: AsyncMock,
    mock_serial_bridge_config_entry: MockConfigEntry,
    service: str,
    status: str,
) -> None:
    """Test light set state service."""

    await setup_integration(menuai, mock_serial_bridge_config_entry)

    assert (state := menuai.states.get(ENTITY_ID))
    assert state.state == STATE_OFF

    # Test set temperature
    await menuai.services.async_call(
        LIGHT_DOMAIN,
        service,
        {ATTR_ENTITY_ID: ENTITY_ID},
        blocking=True,
    )
    mock_serial_bridge.set_device_status.assert_called()

    assert (state := menuai.states.get(ENTITY_ID))
    assert state.state == status
