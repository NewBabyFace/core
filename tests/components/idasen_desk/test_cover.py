"""Test the IKEA Idasen Desk cover."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

from bleak.exc import BleakError
import pytest

from menuai.components.cover import (
    ATTR_CURRENT_POSITION,
    ATTR_POSITION,
    DOMAIN as COVER_DOMAIN,
    CoverState,
)
from menuai.const import (
    SERVICE_CLOSE_COVER,
    SERVICE_OPEN_COVER,
    SERVICE_SET_COVER_POSITION,
    SERVICE_STOP_COVER,
    STATE_UNAVAILABLE,
)
from menuai.core import menuai
from menuai.exceptions import menuaiError

from . import init_integration


async def test_cover_available(
    menuai: menuai,
    mock_desk_api: MagicMock,
) -> None:
    """Test cover available property."""
    entity_id = "cover.test"
    await init_integration(menuai)

    state = menuai.states.get(entity_id)
    assert state
    assert state.state == CoverState.OPEN
    assert state.attributes[ATTR_CURRENT_POSITION] == 60

    mock_desk_api.connect = AsyncMock()
    mock_desk_api.is_connected = False
    mock_desk_api.trigger_update_callback(None)

    state = menuai.states.get(entity_id)
    assert state
    assert state.state == STATE_UNAVAILABLE


@pytest.mark.parametrize(
    ("service", "service_data", "expected_state", "expected_position"),
    [
        (SERVICE_SET_COVER_POSITION, {ATTR_POSITION: 100}, CoverState.OPEN, 100),
        (SERVICE_SET_COVER_POSITION, {ATTR_POSITION: 0}, CoverState.CLOSED, 0),
        (SERVICE_OPEN_COVER, {}, CoverState.OPEN, 100),
        (SERVICE_CLOSE_COVER, {}, CoverState.CLOSED, 0),
        (SERVICE_STOP_COVER, {}, CoverState.OPEN, 60),
    ],
)
async def test_cover_services(
    menuai: menuai,
    mock_desk_api: MagicMock,
    service: str,
    service_data: dict[str, Any],
    expected_state: str,
    expected_position: int,
) -> None:
    """Test cover services."""
    entity_id = "cover.test"
    await init_integration(menuai)
    state = menuai.states.get(entity_id)
    assert state
    assert state.state == CoverState.OPEN
    assert state.attributes[ATTR_CURRENT_POSITION] == 60
    await menuai.services.async_call(
        COVER_DOMAIN,
        service,
        {"entity_id": entity_id, **service_data},
        blocking=True,
    )
    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state
    assert state.state == expected_state
    assert state.attributes[ATTR_CURRENT_POSITION] == expected_position


@pytest.mark.parametrize(
    ("service", "service_data", "mock_method_name"),
    [
        (SERVICE_SET_COVER_POSITION, {ATTR_POSITION: 100}, "move_to"),
        (SERVICE_OPEN_COVER, {}, "move_up"),
        (SERVICE_CLOSE_COVER, {}, "move_down"),
        (SERVICE_STOP_COVER, {}, "stop"),
    ],
)
async def test_cover_services_exception(
    menuai: menuai,
    mock_desk_api: MagicMock,
    service: str,
    service_data: dict[str, Any],
    mock_method_name: str,
) -> None:
    """Test cover services exception handling."""
    entity_id = "cover.test"
    await init_integration(menuai)
    fail_call = getattr(mock_desk_api, mock_method_name)
    fail_call.side_effect = BleakError()
    with pytest.raises(menuaiError):
        await menuai.services.async_call(
            COVER_DOMAIN,
            service,
            {"entity_id": entity_id, **service_data},
            blocking=True,
        )
    await menuai.async_block_till_done()
