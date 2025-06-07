"""Tests for init methods."""

from unittest.mock import AsyncMock

from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from . import setup_integration

from tests.common import MockConfigEntry


async def test_unload_entry(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_flipr_client: AsyncMock,
) -> None:
    """Test unload entry."""

    mock_flipr_client.search_all_ids.return_value = {
        "flipr": ["myfliprid"],
        "hub": ["hubid"],
    }

    await setup_integration(menuai, mock_config_entry)
    assert mock_config_entry.state is ConfigEntryState.LOADED

    await menuai.config_entries.async_unload(mock_config_entry.entry_id)
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED
