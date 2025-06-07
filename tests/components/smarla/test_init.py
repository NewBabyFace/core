"""Test switch platform for Swing2Sleep Smarla integration."""

from unittest.mock import MagicMock

from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from . import setup_integration

from tests.common import MockConfigEntry


async def test_init_invalid_auth(
    menuai: menuai, mock_config_entry: MockConfigEntry, mock_connection: MagicMock
) -> None:
    """Test init invalid authentication behavior."""
    mock_connection.refresh_token.return_value = False

    assert not await setup_integration(menuai, mock_config_entry)

    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR
