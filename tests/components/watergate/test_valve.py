"""Tests for the Watergate valve platform."""

from collections.abc import Generator

from syrupy.assertion import SnapshotAssertion

from menuai.components.valve import DOMAIN as VALVE_DOMAIN, ValveState
from menuai.const import ATTR_ENTITY_ID, SERVICE_CLOSE_VALVE, SERVICE_OPEN_VALVE
from menuai.core import menuai

from . import init_integration

from tests.common import AsyncMock, MockConfigEntry


async def test_change_valve_state_snapshot(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    mock_watergate_client: Generator[AsyncMock],
    mock_entry: MockConfigEntry,
) -> None:
    """Test entities become unavailable after failed update."""
    await init_integration(menuai, mock_entry)

    entity_id = "valve.sonic"

    registered_entity = menuai.states.get(entity_id)
    assert registered_entity
    assert registered_entity.state == ValveState.OPEN
    assert registered_entity == snapshot


async def test_change_valve_state(
    menuai: menuai,
    mock_watergate_client: Generator[AsyncMock],
    mock_entry: MockConfigEntry,
) -> None:
    """Test entities become unavailable after failed update."""
    await init_integration(menuai, mock_entry)

    entity_id = "valve.sonic"

    registered_entity = menuai.states.get(entity_id)
    assert registered_entity
    assert registered_entity.state == ValveState.OPEN

    await menuai.services.async_call(
        VALVE_DOMAIN,
        SERVICE_CLOSE_VALVE,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )

    registered_entity = menuai.states.get(entity_id)
    assert registered_entity
    assert registered_entity.state == ValveState.CLOSING

    mock_watergate_client.async_set_valve_state.assert_called_once_with("closed")
    mock_watergate_client.async_set_valve_state.reset_mock()

    await menuai.services.async_call(
        VALVE_DOMAIN,
        SERVICE_OPEN_VALVE,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )

    registered_entity = menuai.states.get(entity_id)
    assert registered_entity
    assert registered_entity.state == ValveState.OPENING

    mock_watergate_client.async_set_valve_state.assert_called_once_with("open")
