"""Tests for the JVC Projector binary sensor device."""

from unittest.mock import MagicMock

from menuai.core import menuai
from menuai.helpers import entity_registry as er

from tests.common import MockConfigEntry

POWER_ID = "sensor.jvc_projector_power_status"


async def test_entity_state(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    mock_device: MagicMock,
    mock_integration: MockConfigEntry,
) -> None:
    """Tests entity state is registered."""
    state = menuai.states.get(POWER_ID)
    assert state
    assert entity_registry.async_get(state.entity_id)

    assert state.state == "standby"
