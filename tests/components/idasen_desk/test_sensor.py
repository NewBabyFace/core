"""Test the IKEA Idasen Desk sensors."""

from unittest.mock import MagicMock

import pytest

from menuai.const import STATE_UNAVAILABLE
from menuai.core import menuai

from . import init_integration

EXPECTED_INITIAL_HEIGHT = "1"


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_height_sensor(menuai: menuai, mock_desk_api: MagicMock) -> None:
    """Test height sensor."""
    await init_integration(menuai)

    entity_id = "sensor.test_height"
    state = menuai.states.get(entity_id)
    assert state
    assert state.state == EXPECTED_INITIAL_HEIGHT

    mock_desk_api.height = 1.2
    mock_desk_api.trigger_update_callback(None)

    state = menuai.states.get(entity_id)
    assert state
    assert state.state == "1.2"


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_sensor_available(
    menuai: menuai,
    mock_desk_api: MagicMock,
) -> None:
    """Test sensor available property."""
    await init_integration(menuai)

    entity_id = "sensor.test_height"
    state = menuai.states.get(entity_id)
    assert state
    assert state.state == EXPECTED_INITIAL_HEIGHT

    mock_desk_api.is_connected = False
    mock_desk_api.trigger_update_callback(None)

    state = menuai.states.get(entity_id)
    assert state
    assert state.state == STATE_UNAVAILABLE
