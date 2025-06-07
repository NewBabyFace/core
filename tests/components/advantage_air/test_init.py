"""Test the Advantage Air Initialization."""

from unittest.mock import AsyncMock

from advantage_air import ApiError

from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from . import add_mock_config, patch_get


async def test_async_setup_entry(menuai: menuai, mock_get: AsyncMock) -> None:
    """Test a successful setup entry and unload."""

    entry = await add_mock_config(menuai)
    assert entry.state is ConfigEntryState.LOADED

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_async_setup_entry_failure(menuai: menuai) -> None:
    """Test a unsuccessful setup entry."""

    with patch_get(side_effect=ApiError):
        entry = await add_mock_config(menuai)
    assert entry.state is ConfigEntryState.SETUP_RETRY
