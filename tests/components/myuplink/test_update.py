"""Tests for myuplink update module."""

from unittest.mock import AsyncMock

from menuai.core import menuai

from . import setup_integration

from tests.common import MockConfigEntry


async def test_update_states(
    menuai: menuai,
    mock_myuplink_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test update state."""
    await setup_integration(menuai, mock_config_entry)

    state = menuai.states.get("update.gotham_city_firmware")
    assert state is not None
    assert state.state == "off"
