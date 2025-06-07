"""Tests for the IPP integration."""

from unittest.mock import AsyncMock, MagicMock, patch

from pyipp import IPPConnectionError

from menuai.components.ipp.coordinator import IPPDataUpdateCoordinator
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from tests.common import MockConfigEntry


@patch(
    "menuai.components.ipp.coordinator.IPP._request",
    side_effect=IPPConnectionError,
)
async def test_config_entry_not_ready(
    mock_request: MagicMock, menuai: menuai, mock_config_entry: MockConfigEntry
) -> None:
    """Test the IPP configuration entry not ready."""
    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_request.call_count == 1
    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_load_unload_config_entry(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_ipp: AsyncMock,
) -> None:
    """Test the IPP configuration entry loading/unloading."""
    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert isinstance(mock_config_entry.runtime_data, IPPDataUpdateCoordinator)

    await menuai.config_entries.async_unload(mock_config_entry.entry_id)
    await menuai.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED
