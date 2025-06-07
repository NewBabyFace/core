"""Velbus switch platform tests."""

from unittest.mock import AsyncMock, patch

from syrupy.assertion import SnapshotAssertion

from menuai.components.switch import DOMAIN as SWITCH_DOMAIN
from menuai.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    Platform,
)
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import init_integration

from tests.common import MockConfigEntry, snapshot_platform


async def test_entities(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test all entities."""
    with patch("menuai.components.velbus.PLATFORMS", [Platform.SWITCH]):
        await init_integration(menuai, config_entry)

    await snapshot_platform(menuai, entity_registry, snapshot, config_entry.entry_id)


async def test_switch_on_off(
    menuai: menuai,
    mock_relay: AsyncMock,
    config_entry: MockConfigEntry,
) -> None:
    """Test switching relay on and off press."""
    await init_integration(menuai, config_entry)
    # turn off
    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: "switch.living_room_relayname"},
        blocking=True,
    )
    mock_relay.turn_off.assert_called_once_with()
    # turn on
    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: "switch.living_room_relayname"},
        blocking=True,
    )
    mock_relay.turn_on.assert_called_once_with()
